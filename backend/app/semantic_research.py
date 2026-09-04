"""LLM-assisted semantic research passes for SDLC reverse engineering.

The deterministic intelligence modules remain the auditable source of repository facts.
This module adds bounded, one-shot reasoning passes that turn those facts into navigation
and verification briefs for the downstream phase agents.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

from openai import AsyncOpenAI

from .repository_intelligence import RepositoryIntelligence

logger = logging.getLogger(__name__)

RESEARCH_VERSION = "2"
MAX_RESEARCH_INPUT_CHARS = 120_000
MAX_PHASE_INPUT_CHARS = 100_000
MAX_REASONING_FALLBACK_CHARS = 60_000


def _provider_base_url(provider: str) -> str:
    name = provider.strip().lower()
    if name == "openrouter":
        return "https://openrouter.ai/api/v1"
    if name == "openai":
        return "https://api.openai.com/v1"
    raise ValueError(f"Unsupported provider '{provider}'. Supported providers are: openrouter, openai")


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[deterministic intelligence truncated for the research pass]"


def _repository_research_input(intelligence: RepositoryIntelligence) -> str:
    """Build a bounded, high-signal representation of deterministic repository facts."""
    sections = [
        "REPOSITORY INTELLIGENCE SCHEMA: " + intelligence.schema_version,
        f"FILES CONSIDERED: {intelligence.file_count}",
        "LANGUAGES: " + str(intelligence.languages),
        "TECHNOLOGIES: " + ", ".join(intelligence.technologies),
        "PACKAGE SCRIPTS: " + str(intelligence.package_scripts),
        "DEPENDENCIES: " + str(intelligence.dependencies),
        "DEV DEPENDENCIES: " + str(intelligence.dev_dependencies),
        "ENVIRONMENT VARIABLES: " + ", ".join(intelligence.env_variables),
        "ENTRY POINTS:\n" + "\n".join(f"- {x}" for x in intelligence.entry_points[:100]),
        "API ROUTES:\n" + "\n".join(f"- {x}" for x in intelligence.api_routes[:180]),
        "PAGES:\n" + "\n".join(f"- {x}" for x in intelligence.page_files[:180]),
        "DOCUMENTATION EXCERPTS:\n" + "\n\n".join(
            f"### {path}\n{excerpt}" for path, excerpt in list(intelligence.documentation_excerpts.items())[:12]
        ),
        "INTEGRATION FILES:\n" + "\n".join(f"- {x}" for x in intelligence.integration_files[:120]),
        "CONFIG/CI FILES:\n" + "\n".join(f"- {x}" for x in (intelligence.config_files + intelligence.ci_files)[:160]),
        "SOURCE FILES AND SYMBOLS:\n" + "\n".join(
            f"- {item.path} [{item.language or 'unknown'}] imports={item.imports[:12]} exports={item.exports[:12]} symbols={item.symbols}"
            for item in intelligence.source_files[:500]
        ),
        "LOCAL DEPENDENCY EDGES:\n" + "\n".join(
            f"- {edge.source} -> {edge.target}"
            + (f" ({edge.imported_as})" if edge.imported_as else "")
            for edge in intelligence.dependency_edges[:300]
        ),
        "PARSE SUMMARY: " + str(intelligence.parse_summary),
    ]
    return _clip("\n\n".join(sections), MAX_RESEARCH_INPUT_CHARS)


REPOSITORY_RESEARCH_PROMPT = """You are the semantic reconnaissance planner for a repository reverse-engineering system.

You receive deterministic repository intelligence. It contains machine-derived facts and provenance. Produce a concise RESEARCH BRIEF, not final SDLC documentation.

Your job is to construct the semantic map that downstream SDLC phases can use to explore intelligently. Infer cautiously from the evidence. Never present an inference as a verified fact.

The brief MUST contain these sections:
1. Repository identity and likely product/domain
2. Strongly evidenced business/domain concepts
3. Likely actors, users, and system boundaries
4. Candidate business capabilities and representative workflows
5. Important entities/state and relationships suggested by implementation
6. External systems/integrations and their apparent roles
7. Highest-value files/areas to inspect, with WHY each matters
8. Targeted search terms/queries that are likely to reveal business rules or workflow behavior
9. Ambiguities, contradictions, and unsupported assumptions to avoid
10. Cross-phase investigation priorities

For every material hypothesis, include supporting file paths where available and a confidence label (high/medium/low). Prioritize a small number of high-value investigation targets over exhaustive file lists.

This brief is a navigation aid. It must explicitly tell downstream agents to verify material claims in source before using them in final documentation."""


PHASE_RESEARCH_PROMPTS = {
    "business-requirements": """Focus especially on reconstructing business behavior from implementation: actors, goals, capabilities, workflows, validation/business rules, state transitions, permissions, outcomes, external dependencies, and important exceptions. Translate implementation signals into technology-agnostic hypotheses without inventing intent. Identify the exact source files and symbols that should be inspected to verify each major requirement candidate.""",
    "business-purpose": """Focus on product/domain purpose, users, value delivered, major capabilities, and organizational/system boundaries. Identify the strongest evidence for what the software exists to accomplish and what remains uncertain.""",
    "features": """Focus on user-visible capabilities and end-to-end feature workflows. Identify candidate features, their entry points, supporting implementation, and important behavior or limitations that must be verified.""",
    "software-requirements": """Focus on externally observable software behavior: inputs, outputs, APIs, pages, operations, validation, state changes, error handling, and integration contracts. Identify high-value source locations for verification.""",
    "technology-architecture": """Focus on runtime topology, component boundaries, data flow, integrations, deployment/configuration signals, state, caching, and dependency relationships. Identify architecture hypotheses and exact files to verify them.""",
    "design-pattern": """Focus on recurring structural patterns, responsibilities, abstractions, dependency direction, and integration/extension mechanisms. Treat filename conventions only as candidates and identify source evidence needed to establish actual patterns.""",
    "high-level-design": """Focus on logical subsystems, responsibilities, interactions, major data/control flows, external boundaries, and cross-component workflows. Identify source files that can verify each proposed subsystem or interaction.""",
    "low-level-design": """Focus on concrete classes/functions/modules, contracts, control flow, data transformations, validation, state handling, and implementation relationships. Prioritize representative paths rather than cataloguing every symbol.""",
    "implementation-detail": """Focus on concrete implementation mechanisms, algorithms, important functions/classes, dependencies, configuration, error handling, and operational details. Identify exact source evidence that should be inspected.""",
    "testing-harness": """Focus on test strategy, test organization, fixtures, mocks, integration boundaries, coverage signals, and what behavior is actually verified. Identify representative tests and source under test.""",
    "future-directions": """Focus on explicit TODO/debt markers, incomplete areas, brittle boundaries, missing tests, dependency/configuration risks, and evidence-backed improvement opportunities. Separate observed gaps from speculative product ideas.""",
}


def _phase_prompt(phase: str) -> str:
    return PHASE_RESEARCH_PROMPTS.get(
        phase,
        "Focus on the most important evidence, workflows, relationships, and uncertainties relevant to this SDLC phase. Identify exact source locations that should be verified.",
    )


def _extract_message_content(response: Any) -> str | None:
    """Extract assistant text across OpenAI-compatible response variants."""
    choices = getattr(response, "choices", None) or []
    if not choices:
        return None
    message = getattr(choices[0], "message", None)
    if message is None:
        return None

    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()

    # Some reasoning-capable OpenAI-compatible endpoints return content as a list
    # of text objects rather than a single string.
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                continue
            text = getattr(item, "text", None)
            if isinstance(text, str):
                parts.append(text)
        joined = "".join(parts).strip()
        if joined:
            return joined

    # A few providers expose the generated answer through an output_text-like field.
    output_text = getattr(message, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    return None


def _extract_reasoning_fallback(response: Any) -> str | None:
    """Return reasoning only as a bounded diagnostic fallback, never as verified facts."""
    choices = getattr(response, "choices", None) or []
    if not choices:
        return None
    message = getattr(choices[0], "message", None)
    if message is None:
        return None

    for name in ("reasoning", "reasoning_content", "analysis"):
        value = getattr(message, name, None)
        if isinstance(value, str) and value.strip():
            return _clip(value.strip(), MAX_REASONING_FALLBACK_CHARS)
    return None


def _response_diagnostics(response: Any) -> dict[str, Any]:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return {"choices": 0}
    message = getattr(choices[0], "message", None)
    return {
        "choices": len(choices),
        "finish_reason": getattr(choices[0], "finish_reason", None),
        "message_content_type": type(getattr(message, "content", None)).__name__ if message else None,
        "has_reasoning": bool(message and any(getattr(message, name, None) for name in ("reasoning", "reasoning_content", "analysis"))),
    }


async def _one_shot_chat(*, provider: str, model: str, api_key: str, system_prompt: str, user_prompt: str) -> str:
    client = AsyncOpenAI(base_url=_provider_base_url(provider), api_key=api_key.strip())
    try:
        response = await client.chat.completions.create(
            model=model.strip(),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.1,
        )
        content = _extract_message_content(response)
        diagnostics = _response_diagnostics(response)
        logger.info("SEMANTIC_RESEARCH response model=%s provider=%s diagnostics=%s", model, provider, diagnostics)
        if content:
            return content

        reasoning = _extract_reasoning_fallback(response)
        if reasoning:
            logger.warning("SEMANTIC_RESEARCH model returned reasoning without answer; failing closed instead of treating reasoning as the research brief")
            raise RuntimeError(
                "Research LLM returned reasoning but no final answer. "
                f"finish_reason={diagnostics.get('finish_reason')}; reasoning_chars={len(reasoning)}"
            )
        raise RuntimeError(
            "Research LLM returned an empty response. "
            f"finish_reason={diagnostics.get('finish_reason')}; response_diagnostics={json.dumps(diagnostics, default=str)}"
        )
    finally:
        await client.close()


def run_repository_research(*, intelligence: RepositoryIntelligence, provider: str, model: str, api_key: str) -> str:
    """Run exactly one model request for repository-level semantic reconnaissance."""
    if not api_key or not api_key.strip():
        raise ValueError("An API key is required for repository research")
    return asyncio.run(_one_shot_chat(
        provider=provider,
        model=model,
        api_key=api_key,
        system_prompt=REPOSITORY_RESEARCH_PROMPT,
        user_prompt=_repository_research_input(intelligence),
    ))


def run_phase_research(*, phase: str, phase_intelligence: str, repository_research: str, provider: str, model: str, api_key: str) -> str:
    """Run exactly one model request to specialize repository reconnaissance for a phase."""
    if not api_key or not api_key.strip():
        raise ValueError(f"An API key is required for phase research '{phase}'")
    user_prompt = _clip(
        "REPOSITORY-LEVEL RESEARCH BRIEF:\n" + repository_research
        + "\n\nDETERMINISTIC PHASE INTELLIGENCE:\n" + phase_intelligence
        + "\n\nPHASE FOCUS:\n" + _phase_prompt(phase)
        + "\n\nProduce a phase research brief. Do not write final documentation. Include: (a) candidate findings, (b) evidence chains with file paths/symbols, (c) prioritized files to inspect, (d) targeted searches, (e) verification obligations, and (f) ambiguities/unknowns. Clearly label hypotheses and confidence.",
        MAX_PHASE_INPUT_CHARS,
    )
    return asyncio.run(_one_shot_chat(
        provider=provider,
        model=model,
        api_key=api_key,
        system_prompt="""You are the phase-specific semantic research planner in an evidence-driven SDLC reverse-engineering pipeline.

The repository research brief is upstream reasoning, not authoritative evidence. Deterministic intelligence is machine-derived evidence, but it can still be incomplete. Your output is a navigation and verification brief, never final documentation.

Do not encourage the downstream agent to skip repository inspection. Instead, make its first inspections highly targeted. For each material hypothesis, name the exact file/symbol/search target that can confirm or reject it. Flag unsupported assumptions explicitly.

The downstream agent must verify material claims against repository source before including them in the final artifact.

A final answer is REQUIRED. Do not stop after internal reasoning. Return the research brief itself as the assistant answer, even if some sections are uncertain.""",
        user_prompt=user_prompt,
    ))


def write_research_artifact(path: Path, *, kind: str, phase: Optional[str], content: str) -> None:
    """Persist a human-readable research brief for diagnostics and later inspection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        f"# {kind.title()} Research Brief",
        "",
        f"Research schema: {RESEARCH_VERSION}",
        f"Phase: {phase or 'repository-wide'}",
        "",
        "> This is an upstream reasoning artifact. It is not authoritative evidence or final SDLC documentation. Material claims must be verified against repository source.",
        "",
    ]
    path.write_text("\n".join(header) + content + "\n", encoding="utf-8")
