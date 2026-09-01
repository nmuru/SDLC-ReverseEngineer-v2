"""OpenAI Agents SDK phase runner for repository reverse engineering."""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

from agents import Agent, Runner, function_tool
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENCODE_SKILLS_SOURCE = PROJECT_ROOT / ".opencode" / "skills"


class AgentRunnerError(RuntimeError):
    """Raised when a repository-analysis phase cannot be completed."""


def _clone_repository(repo_url: str, workspace: Path) -> Path:
    repository = workspace / "target-repository"
    if repository.exists():
        shutil.rmtree(repository, ignore_errors=True)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url.strip(), str(repository)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    if result.returncode != 0:
        raise AgentRunnerError("Could not clone the target repository: " + result.stderr.strip()[:2000])
    return repository


def _read_skill(phase: str) -> str:
    if not OPENCODE_SKILLS_SOURCE.exists():
        return ""
    candidates = [
        OPENCODE_SKILLS_SOURCE / phase / "SKILL.md",
        OPENCODE_SKILLS_SOURCE / f"{phase}.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8", errors="replace")
    return ""


def _build_tools(repository: Path):
    root = repository.resolve()

    def safe_path(relative_path: str) -> Path:
        path = (root / relative_path).resolve()
        if path != root and root not in path.parents:
            raise ValueError("Path must remain inside the repository")
        return path

    @function_tool
    def list_files(path: str = ".", max_entries: int = 300) -> str:
        """List repository files and directories recursively, without modifying anything."""
        target = safe_path(path)
        if not target.exists():
            return "Path does not exist."
        entries = []
        for item in target.rglob("*"):
            if ".git" in item.parts:
                continue
            entries.append(str(item.relative_to(root)))
            if len(entries) >= max_entries:
                entries.append("[truncated]")
                break
        return "\n".join(entries)

    @function_tool
    def read_file(path: str, max_chars: int = 30000) -> str:
        """Read a UTF-8 text file from the repository. Use this to inspect source and configuration files."""
        target = safe_path(path)
        if not target.is_file():
            return "File does not exist or is not a regular file."
        try:
            return target.read_text(encoding="utf-8", errors="replace")[:max_chars]
        except OSError as exc:
            return f"Could not read file: {exc}"

    @function_tool
    def search_repository(query: str, max_results: int = 100) -> str:
        """Search repository text files for a literal string and return matching file paths and lines."""
        matches = []
        for item in root.rglob("*"):
            if ".git" in item.parts or not item.is_file():
                continue
            try:
                with item.open("r", encoding="utf-8", errors="replace") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if query.lower() in line.lower():
                            matches.append(f"{item.relative_to(root)}:{line_number}: {line.rstrip()}")
                            if len(matches) >= max_results:
                                return "\n".join(matches + ["[truncated]"])
            except OSError:
                continue
        return "\n".join(matches) if matches else "No matches found."

    return [list_files, read_file, search_repository]


def _summarize_item(item) -> dict:
    """Return compact diagnostics metadata without dumping large contents."""
    item_type = type(item).__name__
    data = {"type": item_type}
    for attr in ("raw_item", "item", "output", "name", "arguments"):
        if hasattr(item, attr):
            value = getattr(item, attr)
            if attr == "arguments" and isinstance(value, str):
                data[attr] = value[:1000]
            elif attr in {"name"}:
                data[attr] = str(value)
            elif attr in {"output"}:
                text = str(value)
                data[attr] = text[:500]
    return data


async def _run_agent(*, phase: str, phase_name: str, repository: Path, model: str, api_key: str, provider: str, previous_output: Optional[str]) -> str:
    provider_name = provider.strip().lower()
    if provider_name == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
    elif provider_name == "openai":
        base_url = "https://api.openai.com/v1"
    else:
        raise AgentRunnerError(f"Unsupported provider '{provider}'. Supported providers are: openrouter, openai")

    skill = _read_skill(phase)
    handoff = ""
    if previous_output:
        handoff = "\n\nPrevious phase output is supporting context only. Verify important claims against repository evidence.\n\n" + previous_output[:20000]

    instructions = f"""You are performing the {phase_name} phase of an evidence-driven SDLC reverse-engineering workflow.
The tools provide read-only access to the cloned repository. Inspect the repository directly before drawing conclusions. Do not invent details. Distinguish verified facts, reasonable inferences, and unknowns when evidence is incomplete.

Follow this phase methodology:\n{skill or 'Inspect the repository and produce rigorous documentation for the requested phase.'}

Return only complete professional Markdown documentation for this phase. Do not describe the agent, tools, prompts, or execution process.""" + handoff

    client = AsyncOpenAI(base_url=base_url, api_key=api_key.strip())
    agent = Agent(
        name=f"SDLC {phase_name}",
        instructions=instructions,
        model=OpenAIChatCompletionsModel(model=model.strip(), openai_client=client),
        tools=_build_tools(repository),
    )

    trace_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    logger.warning(
        "AGENT_DIAG start trace_id=%s phase=%s model=%s provider=%s repository=%s",
        trace_id, phase, model, provider_name, repository,
    )

    result = await Runner.run(agent, "Analyze the repository and produce the requested phase documentation.")

    elapsed = time.perf_counter() - started
    usage = getattr(result, "context_wrapper", None)
    usage_info = getattr(getattr(usage, "usage", None), "requests", None)
    new_items = getattr(result, "new_items", []) or []
    raw_responses = getattr(result, "raw_responses", []) or []
    logger.warning(
        "AGENT_DIAG end trace_id=%s phase=%s elapsed_s=%.3f new_items=%d raw_responses=%d request_usage=%s",
        trace_id, phase, elapsed, len(new_items), len(raw_responses), usage_info,
    )
    for index, item in enumerate(new_items):
        logger.warning(
            "AGENT_DIAG item trace_id=%s index=%d details=%s",
            trace_id, index, json.dumps(_summarize_item(item), ensure_ascii=False, default=str),
        )

    output = str(result.final_output or "").strip()
    if not output:
        logger.warning(
            "AGENT_DIAG empty_final_output trace_id=%s phase=%s new_items=%d raw_responses=%d",
            trace_id, phase, len(new_items), len(raw_responses),
        )
        raise AgentRunnerError(f"OpenAI Agents SDK completed phase '{phase}' but returned no final output.")
    return output


def run_phase_agent(phase: str, phase_name: str, workspace: Path, repo_url: str, previous_output: Optional[str] = None, provider: str = "openrouter", model: str = "openrouter/free", api_key: Optional[str] = None) -> str:
    """Run one repository-analysis phase using the OpenAI Agents SDK."""
    if not api_key or not api_key.strip():
        raise AgentRunnerError(f"An API key is required for provider '{provider}'.")
    workspace.mkdir(parents=True, exist_ok=True)
    repository = _clone_repository(repo_url, workspace)
    try:
        return asyncio.run(_run_agent(
            phase=phase, phase_name=phase_name, repository=repository,
            model=model, api_key=api_key, provider=provider, previous_output=previous_output,
        ))
    except AgentRunnerError:
        raise
    except Exception as exc:
        logger.exception("OpenAI Agents SDK failed during phase %s", phase)
        raise AgentRunnerError(f"OpenAI Agents SDK failed during phase '{phase}': {exc}") from exc
