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
from typing import Any, Optional

from agents import Agent, Runner, RunHooks, function_tool
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


def _preview(value: Any, limit: int = 800) -> str:
    text = str(value).replace("\n", "\\n")
    return text[:limit] + ("...[truncated]" if len(text) > limit else "")


def _extract_value(item: Any, *names: str) -> Any:
    if isinstance(item, dict):
        for name in names:
            if item.get(name) is not None:
                return item[name]
    for name in names:
        if hasattr(item, name):
            value = getattr(item, name)
            if value is not None:
                return value
    return None


def _summarize_item(item: Any) -> dict:
    """Return compact diagnostics metadata without dumping full repository contents."""
    data = {"python_type": type(item).__name__}
    item_type = _extract_value(item, "type")
    role = _extract_value(item, "role")
    if item_type is not None:
        data["type"] = str(item_type)
    if role is not None:
        data["role"] = str(role)

    name = _extract_value(item, "name")
    call_id = _extract_value(item, "call_id", "tool_call_id")
    arguments = _extract_value(item, "arguments")
    output = _extract_value(item, "output")
    content = _extract_value(item, "content")

    if name is not None:
        data["name"] = str(name)
    if call_id is not None:
        data["call_id"] = str(call_id)
    if arguments is not None:
        data["arguments_chars"] = len(str(arguments))
        data["arguments_preview"] = _preview(arguments, 300)
    if output is not None:
        data["output_chars"] = len(str(output))
        data["output_preview"] = _preview(output, 400)
    if content is not None:
        data["content_chars"] = len(str(content))
        data["content_preview"] = _preview(content, 400)

    # Some SDK/provider items expose their payload only through serialization.
    # Record safe top-level metadata so dict inputs are no longer anonymous.
    if isinstance(item, dict):
        data["keys"] = sorted(str(key) for key in item.keys())
        for key in ("function", "tool_calls", "tool_call"):
            if key in item and key not in data:
                value = item[key]
                data[f"{key}_chars"] = len(str(value))
                data[f"{key}_preview"] = _preview(value, 400)
    else:
        raw = getattr(item, "__dict__", None)
        if isinstance(raw, dict):
            data["keys"] = sorted(str(key) for key in raw.keys() if not str(key).startswith("_"))

    return data


class AgentDiagnosticsHooks(RunHooks):
    """Logs every SDK lifecycle event, including failed runs."""

    def __init__(self, trace_id: str, phase: str):
        self.trace_id = trace_id
        self.phase = phase
        self.llm_turn = 0
        self.tool_calls = 0

    async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:
        self.llm_turn += 1
        summaries = [_summarize_item(item) for item in input_items]
        logger.warning(
            "AGENT_DIAG llm_start trace_id=%s phase=%s turn=%d input_items=%d system_prompt_chars=%d input=%s",
            self.trace_id,
            self.phase,
            self.llm_turn,
            len(input_items),
            len(system_prompt or ""),
            json.dumps(summaries, ensure_ascii=False, default=str),
        )

    async def on_llm_end(self, context, agent, response) -> None:
        output_items = getattr(response, "output", []) or []
        summaries = [_summarize_item(item) for item in output_items]
        usage = getattr(context, "usage", None)
        logger.warning(
            "AGENT_DIAG llm_end trace_id=%s phase=%s turn=%d output_items=%d usage_requests=%s output=%s",
            self.trace_id,
            self.phase,
            self.llm_turn,
            len(output_items),
            getattr(usage, "requests", None),
            json.dumps(summaries, ensure_ascii=False, default=str),
        )

    async def on_tool_start(self, context, agent, tool) -> None:
        self.tool_calls += 1
        logger.warning(
            "AGENT_DIAG tool_start trace_id=%s phase=%s turn=%d tool_index=%d tool=%s call_id=%s arguments=%s",
            self.trace_id,
            self.phase,
            self.llm_turn,
            self.tool_calls,
            getattr(tool, "name", type(tool).__name__),
            getattr(context, "tool_call_id", None),
            _preview(getattr(context, "tool_arguments", None), 1000),
        )

    async def on_tool_end(self, context, agent, tool, result) -> None:
        logger.warning(
            "AGENT_DIAG tool_end trace_id=%s phase=%s turn=%d tool_index=%d tool=%s call_id=%s result_chars=%d result_preview=%s",
            self.trace_id,
            self.phase,
            self.llm_turn,
            self.tool_calls,
            getattr(tool, "name", type(tool).__name__),
            getattr(context, "tool_call_id", None),
            len(str(result)),
            _preview(result, 1200),
        )

    async def on_agent_end(self, context, agent, output) -> None:
        logger.warning(
            "AGENT_DIAG agent_end trace_id=%s phase=%s turns=%d tool_calls=%d output_preview=%s",
            self.trace_id,
            self.phase,
            self.llm_turn,
            self.tool_calls,
            _preview(output, 1000),
        )


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
    hooks = AgentDiagnosticsHooks(trace_id, phase)
    started = time.perf_counter()
    logger.warning(
        "AGENT_DIAG start trace_id=%s phase=%s model=%s provider=%s repository=%s",
        trace_id, phase, model, provider_name, repository,
    )

    try:
        result = await Runner.run(
            agent,
            "Analyze the repository and produce the requested phase documentation.",
            hooks=hooks,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started
        logger.warning(
            "AGENT_DIAG failed trace_id=%s phase=%s elapsed_s=%.3f turns_observed=%d tool_calls_observed=%d error_type=%s error=%s",
            trace_id,
            phase,
            elapsed,
            hooks.llm_turn,
            hooks.tool_calls,
            type(exc).__name__,
            str(exc),
        )
        raise

    elapsed = time.perf_counter() - started
    usage = getattr(result, "context_wrapper", None)
    usage_info = getattr(getattr(usage, "usage", None), "requests", None)
    new_items = getattr(result, "new_items", []) or []
    raw_responses = getattr(result, "raw_responses", []) or []
    logger.warning(
        "AGENT_DIAG end trace_id=%s phase=%s elapsed_s=%.3f turns_observed=%d tool_calls_observed=%d new_items=%d raw_responses=%d request_usage=%s",
        trace_id, phase, elapsed, hooks.llm_turn, hooks.tool_calls, len(new_items), len(raw_responses), usage_info,
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
