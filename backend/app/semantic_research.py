"""LLM-assisted semantic summaries for SDLC reverse engineering.

The deterministic intelligence modules remain the auditable source of repository facts.
This module adds bounded, one-shot reasoning passes that summarize those supplied facts
for downstream phase agents.
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


REPOSITORY_RESEARCH_PROMPT = """You summarize repository facts that have already been extracted by the program.

The repository was already scanned before this request. The supplied REPOSITORY INTELLIGENCE is the source material for this task. Do not perform repository discovery in your response.

Your task is to interpret those supplied facts and produce a compact narrative summary that helps downstream SDLC phases understand the repository.

Treat the supplied intelligence as input data, not as a request to inspect the repository. Do not act like a coding agent. Do not create a research plan. Do not decide which files should be opened next. Do not enumerate repository files or generate search queries. Do not describe an investigation process.

Use file paths only when they directly support an important statement. A path is evidence for a statement; it is not an item to investigate.

Summarize only what can reasonably be inferred from the supplied information:
1. Repository identity and likely product/domain
2. Strongly supported business/domain concepts
3. Likely users, actors, and system boundaries
4. Major capabilities and representative workflows visible in the supplied evidence
5. Important entities, state, and relationships suggested by the supplied evidence
6. External systems/integrations and their apparent roles
7. Important implementation characteristics relevant across SDLC phases
8. Ambiguities, contradictions, or areas where the supplied evidence is insufficient

Rules:
- Target 700-1,200 words. Never exceed 1,500 words.
- Do not list files simply because they appear in the input.
- Do not repeat a fact or path across multiple sections.
- Do not write "need to verify" repeatedly.
- Do not invent product intent that is not supported by the supplied evidence.
- Clearly distinguish strong evidence from reasonable inference.
- When many paths show the same pattern, state the pattern and cite one or two representative paths.
- Begin directly with the repository summary. Do not discuss these instructions or your reasoning process.

The output is a summary of the supplied repository intelligence. It is not a replacement for source verification by downstream agents."""


PHASE_RESEARCH_PROMPTS = {
    "business-requirements": """Summarize the business behavior that is already visible in the supplied repository intelligence: actors, goals, capabilities, workflows, validation, business rules, state changes, permissions, outcomes, dependencies, and notable exceptions. Convert implementation signals into cautious, technology-agnostic interpretations. Do not propose files to inspect or a research plan.""",
    "business-purpose": """Summarize the product/domain purpose, likely users, value delivered, major capabilities, and system boundaries already suggested by the supplied repository intelligence. Focus on what the supplied evidence says, not on what should be investigated next.""",
    "features": """Summarize the user-visible capabilities and representative end-to-end workflows already suggested by the supplied repository intelligence. Mention representative evidence paths only when they support an important capability. Do not create an exploration plan.""",
    "software-requirements": """Summarize externally observable behavior already indicated by the supplied repository intelligence: inputs, outputs, APIs, pages, operations, validation, state changes, error handling, and integration behavior. Do not plan further repository inspection.""",
    "technology-architecture": """Summarize the runtime structure, component relationships, data flow, integrations, configuration, state, caching, and dependency relationships already indicated by the supplied repository intelligence. Distinguish evidence from inference and do not propose an inspection plan.""",
    "design-pattern": """Summarize recurring structural patterns, responsibilities, abstractions, dependency direction, and integration mechanisms that can already be inferred from the supplied repository intelligence. Treat names and paths as evidence, not as a reason to enumerate or inspect files.""",
    "high-level-design": """Summarize the logical subsystems, responsibilities, interactions, major data/control flows, and external boundaries already suggested by the supplied repository intelligence. Do not produce a list of files to inspect.""",
    "low-level-design": """Summarize important modules, functions, contracts, control flow, data transformations, validation, state handling, and implementation relationships already visible in the supplied repository intelligence. Focus on representative evidence rather than cataloguing symbols.""",
    "implementation-detail": """Summarize important implementation mechanisms, algorithms, functions/classes, dependencies, configuration, error handling, and operational details already visible in the supplied repository intelligence. Do not create a discovery or verification plan.""",
    "testing-harness": """Summarize the test strategy, test organization, fixtures, mocks, integration boundaries, coverage signals, and behavior verification already visible in the supplied repository intelligence. Do not produce a list of tests or files to inspect next.""",
    "future-directions": """Summarize evidence-backed gaps, explicit TODO/debt markers, incomplete areas, missing tests, brittle boundaries, and dependency/configuration risks already visible in the supplied repository intelligence. Separate observed gaps from speculation.""",
}


def _phase_prompt(phase: str) -> str:
    return PHASE_RESEARCH_PROMPTS.get(
        phase,
        "Summarize the most important evidence, behavior, relationships, and uncertainties relevant to this SDLC phase using only the supplied repository intelligence. Do not propose further investigation.",
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
    """Run exactly one model request to summarize supplied repository intelligence."""
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
    """Run exactly one model request to summarize supplied phase-relevant intelligence."""
    if not api_key or not api_key.strip():
        raise ValueError(f"An API key is required for phase research '{phase}'")
    user_prompt = _clip(
        "REPOSITORY SUMMARY:\n" + repository_research
        + "\n\nDETERMINISTIC PHASE INTELLIGENCE:\n" + phase_intelligence
        + "\n\nPHASE FOCUS:\n" + _phase_prompt(phase)
        + "\n\nUsing only the supplied repository summary and deterministic phase intelligence, write a compact phase summary. Do not inspect, rediscover, enumerate, or plan further repository investigation. Do not produce file lists, search queries, or verification plans. State the strongest phase-relevant interpretations, supporting evidence, and important uncertainties. Use representative paths only where they directly support a statement. Target 500-900 words and never exceed 1,200 words. Begin directly with the summary.",
        MAX_PHASE_INPUT_CHARS,
    )
    return asyncio.run(_one_shot_chat(
        provider=provider,
        model=model,
        api_key=api_key,
        system_prompt="""You summarize phase-relevant facts that have already been extracted by the program.

The repository has already been scanned, and a repository summary has already been produced. The supplied repository summary and deterministic phase intelligence are the source material for this task.

Do not act as a coding agent. Do not inspect the repository in your response. Do not generate a research plan, investigation plan, file inventory, search list, or verification checklist. Do not describe what a downstream agent should inspect.

Your task is to interpret the supplied material for the selected SDLC phase. Summarize the strongest evidence-supported findings, representative evidence paths, reasonable inferences, and important uncertainties. Paths are citations for claims, not work items.

Keep the response compact and finite. Target 500-900 words and never exceed 1,200 words. Do not repeat the same claim or path. Do not narrate your reasoning or discuss these instructions. Begin directly with the phase summary.

The supplied material is not authoritative beyond what it explicitly supports. Do not invent missing intent or behavior. When evidence is insufficient, state the uncertainty briefly and move on.""",
        user_prompt=user_prompt,
    ))


def write_research_artifact(path: Path, *, kind: str, phase: Optional[str], content: str) -> None:
    """Persist a human-readable research summary for diagnostics and later inspection."""
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
