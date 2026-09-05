"""OpenAI Agents SDK phase runner for repository reverse engineering."""

import asyncio
import json
import logging
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from agents import Agent, Runner, RunHooks, function_tool
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from .config import settings

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_SOURCE = PROJECT_ROOT / ".agents" / "agents"
SKILLS_SOURCE = PROJECT_ROOT / ".agents" / "skills"


class AgentRunnerError(RuntimeError):
    """Raised when a repository-analysis phase cannot be completed."""


def github_repository_size_bytes(repo_url: str) -> int | None:
    """Return GitHub's repository-size estimate in bytes for a public GitHub URL."""
    parsed = urlparse(repo_url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    owner, repository = parts[0], parts[1]
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository:
        return None
    api_url = f"https://api.github.com/repos/{owner}/{repository}"
    request = Request(api_url, headers={"Accept": "application/vnd.github+json", "User-Agent": "sdlc-reverse-engineer"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise AgentRunnerError("Could not inspect the GitHub repository before cloning. The repository may not exist or may not be publicly accessible.") from exc
        raise AgentRunnerError(f"Could not inspect the GitHub repository before cloning: HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise AgentRunnerError(f"Could not inspect the GitHub repository before cloning: {exc}") from exc
    size_kib = payload.get("size")
    if not isinstance(size_kib, int) or size_kib < 0:
        return None
    return size_kib * 1024


def clone_repository(repo_url: str, workspace: Path) -> Path:
    """Clone a repository once for the lifetime of an analysis run."""
    repository = workspace / "target-repository"
    if repository.exists():
        shutil.rmtree(repository, ignore_errors=True)
    result = subprocess.run(["git", "clone", "--depth", "1", repo_url.strip(), str(repository)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if result.returncode != 0:
        raise AgentRunnerError("Could not clone the target repository: " + result.stderr.strip()[:2000])
    return repository


def repository_size_bytes(repository: Path) -> int:
    """Return the on-disk size of the cloned repository, including Git metadata."""
    total = 0
    try:
        for path in repository.rglob("*"):
            if path.is_file():
                try:
                    total += path.stat().st_size
                except OSError:
                    continue
    except OSError as exc:
        raise AgentRunnerError(f"Could not measure cloned repository size: {exc}") from exc
    return total


def _read_agent_definition(phase: str) -> str:
    """Load the phase-specific agent contract when present."""
    if not AGENTS_SOURCE.exists():
        return ""
    candidate = AGENTS_SOURCE / f"{phase}.md"
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8", errors="replace")
    return ""


def _read_skill(phase: str) -> str:
    """Load the complete phase skill eagerly, as in the current implementation."""
    if not SKILLS_SOURCE.exists():
        return ""
    candidates = [SKILLS_SOURCE / phase / "SKILL.md", SKILLS_SOURCE / phase / "SKILL.md"]
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
        """Read a UTF-8 text file for conditional follow-up evidence not already present in deterministic intelligence."""
        target = safe_path(path)
        if not target.is_file():
            return "File does not exist or is not a regular file."
        try:
            return target.read_text(encoding="utf-8", errors="replace")[:max_chars]
        except OSError as exc:
            return f"Could not read file: {exc}"

    @function_tool
    def search_repository(query: str, max_results: int = 100) -> str:
        """Search repository text for conditional follow-up evidence not already present in deterministic intelligence."""
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


class AgentDiagnosticsHooks(RunHooks):
    def __init__(self, trace_id: str, phase: str):
        self.trace_id = trace_id
        self.phase = phase
        self.llm_turn = 0
        self.tool_calls = 0

    async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:
        self.llm_turn += 1
        logger.warning("AGENT_DIAG llm_start trace_id=%s phase=%s turn=%d input_items=%d system_prompt_chars=%d", self.trace_id, self.phase, self.llm_turn, len(input_items), len(system_prompt or ""))

    async def on_llm_end(self, context, agent, response) -> None:
        output_items = getattr(response, "output", []) or []
        usage = getattr(context, "usage", None)
        logger.warning("AGENT_DIAG llm_end trace_id=%s phase=%s turn=%d output_items=%d usage_requests=%s", self.trace_id, self.phase, self.llm_turn, len(output_items), getattr(usage, "requests", None))

    async def on_tool_start(self, context, agent, tool) -> None:
        self.tool_calls += 1
        logger.warning("AGENT_DIAG tool_start trace_id=%s phase=%s turn=%d tool_index=%d tool=%s", self.trace_id, self.phase, self.llm_turn, self.tool_calls, getattr(tool, "name", type(tool).__name__))

    async def on_tool_end(self, context, agent, tool, result) -> None:
        logger.warning("AGENT_DIAG tool_end trace_id=%s phase=%s turn=%d tool_index=%d tool=%s result_chars=%d result_preview=%s", self.trace_id, self.phase, self.llm_turn, self.tool_calls, getattr(tool, "name", type(tool).__name__), len(str(result)), _preview(result, 1200))

    async def on_agent_end(self, context, agent, output) -> None:
        logger.warning("AGENT_DIAG agent_end trace_id=%s phase=%s turns=%d tool_calls=%d output_preview=%s", self.trace_id, self.phase, self.llm_turn, self.tool_calls, _preview(output, 1000))


async def _run_agent(*, phase: str, phase_name: str, repository: Path, phase_intelligence: str, model: str, api_key: str, provider: str, previous_output: Optional[str]) -> str:
    provider_name = provider.strip().lower()
    if provider_name == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
    elif provider_name == "openai":
        base_url = "https://api.openai.com/v1"
    else:
        raise AgentRunnerError(f"Unsupported provider '{provider}'. Supported providers are: openrouter, openai")

    agent_definition = _read_agent_definition(phase)
    skill = _read_skill(phase)
    handoff = ""
    if previous_output:
        handoff = "\n\nPrevious phase output is supporting context only. Verify important claims against repository evidence.\n\n" + previous_output[:20000]

    common_instructions = """You are performing an evidence-driven SDLC reverse-engineering phase.
The repository has already been cloned and deterministic repository intelligence has already been collected before your first turn. Treat that intelligence as the primary evidence index.
Do not repeat repository-wide discovery or reread files merely to reconstruct information already present in the intelligence package. Use repository tools only for a specific ambiguity, missing source passage, or precision check.
Do not invent details. Distinguish verified facts, reasonable inferences, and unknowns when evidence is incomplete.
The repository is read-only. Do not modify it.
Return only complete professional Markdown documentation for the requested phase. Do not describe the agent, tools, prompts, intelligence collection, or execution process.

INVESTIGATION BUDGET
You have a finite investigation budget defined by the runner. Prioritize high-value evidence gathering early. As the remaining budget becomes small, stop broad exploration and transition to verification and synthesis. On the final available turn, produce the best-supported artifact possible rather than continuing investigation. Never invent missing evidence; mark it unknown or unverified."""

    instructions = "\n\n".join(part for part in [common_instructions, agent_definition, f"Phase methodology:\n{skill}" if skill else "", phase_intelligence, handoff] if part)

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
    logger.warning("AGENT_DIAG start trace_id=%s phase=%s model=%s provider=%s repository=%s intelligence_chars=%d agent_definition_chars=%d skill_chars=%d max_turns=%d", trace_id, phase, model, provider_name, repository, len(phase_intelligence), len(agent_definition), len(skill), settings.phase_agent_max_turns)
    try:
        result = await Runner.run(agent, "Analyze the repository and produce the requested phase documentation.", hooks=hooks, max_turns=settings.phase_agent_max_turns)
    except Exception as exc:
        logger.warning("AGENT_DIAG failed trace_id=%s phase=%s elapsed_s=%.3f turns_observed=%d tool_calls_observed=%d error_type=%s error=%s", trace_id, phase, time.perf_counter() - started, hooks.llm_turn, hooks.tool_calls, type(exc).__name__, str(exc))
        raise
    output = str(result.final_output or "").strip()
    if not output:
        raise AgentRunnerError(f"OpenAI Agents SDK completed phase '{phase}' but returned no final output.")
    return output


def run_phase_agent(phase: str, phase_name: str, repository: Path, phase_intelligence: str, previous_output: Optional[str] = None, provider: str = "openrouter", model: str = "openrouter/free", api_key: Optional[str] = None) -> str:
    """Run one phase against a shared read-only repository workspace."""
    if not api_key or not api_key.strip():
        raise AgentRunnerError(f"An API key is required for provider '{provider}'.")
    if not repository.is_dir():
        raise AgentRunnerError(f"Repository path does not exist: {repository}")
    try:
        return asyncio.run(_run_agent(phase=phase, phase_name=phase_name, repository=repository, phase_intelligence=phase_intelligence, model=model, api_key=api_key, provider=provider, previous_output=previous_output))
    except AgentRunnerError:
        raise
    except Exception as exc:
        logger.exception("OpenAI Agents SDK failed during phase %s", phase)
        raise AgentRunnerError(f"OpenAI Agents SDK failed during phase '{phase}': {exc}") from exc
