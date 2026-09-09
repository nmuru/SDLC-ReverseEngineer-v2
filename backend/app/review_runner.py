"""Cross-phase Review Code Base runner."""

import asyncio
import json
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from agents import Agent, Runner, RunHooks, function_tool
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from .agent_runner import _build_tools, _read_agent_definition, _read_skill, clone_repository
from .config import settings
from .renderer import render_analysis
from .run_control import RunCancelled, RunControl


class ReviewRunnerError(RuntimeError):
    """Raised when the cross-phase review cannot be completed."""


class ReviewDiagnostics(RunHooks):
    def __init__(self, review_id: str):
        self.review_id = review_id
        self.turns = 0
        self.tool_calls = 0

    async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:
        self.turns += 1

    async def on_tool_start(self, context, agent, tool) -> None:
        self.tool_calls += 1


def _artifact_catalog(output_run_dir: Path) -> list[dict]:
    artifacts = []
    if not output_run_dir.exists():
        return artifacts
    for phase_dir in sorted(output_run_dir.iterdir()):
        if not phase_dir.is_dir() or phase_dir.name == "review-code-base":
            continue
        raw_path = phase_dir / "raw.md"
        if not raw_path.is_file():
            continue
        try:
            line_count = sum(1 for _ in raw_path.open("r", encoding="utf-8", errors="replace"))
            size = raw_path.stat().st_size
        except OSError:
            continue
        artifacts.append({"phase": phase_dir.name, "file": f"{phase_dir.name}/raw.md", "lines": line_count, "bytes": size})
    return artifacts


def _build_review_tools(repository: Path, output_run_dir: Path):
    tools = list(_build_tools(repository))
    output_root = output_run_dir.resolve()

    def safe_output_path(phase: str) -> Path:
        if not phase or Path(phase).name != phase:
            raise ValueError("Invalid phase artifact name")
        path = (output_root / phase / "raw.md").resolve()
        if output_root not in path.parents:
            raise ValueError("Artifact path must remain inside the analysis output")
        return path

    @function_tool
    def list_output_artifacts() -> str:
        """List generated SDLC artifacts available for this review. Returns metadata only, not document contents."""
        return json.dumps(_artifact_catalog(output_run_dir), indent=2)

    @function_tool
    def read_output_artifact(phase: str, max_chars: int = 24000) -> str:
        """Read one generated phase artifact on demand. Use the phase name from list_output_artifacts."""
        path = safe_output_path(phase)
        if not path.is_file():
            return "Artifact does not exist."
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"Could not read artifact: {exc}"
        return content[:max_chars]

    return tools + [list_output_artifacts, read_output_artifact]


async def _run_review(*, repository: Path, output_run_dir: Path, provider: str, model: str, api_key: str, run_control: Optional[RunControl] = None) -> tuple[str, str, int, int]:
    provider_name = provider.strip().lower()
    if provider_name == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
    elif provider_name == "openai":
        base_url = "https://api.openai.com/v1"
    else:
        raise ReviewRunnerError(f"Unsupported provider '{provider}'")

    artifacts = _artifact_catalog(output_run_dir)
    if not artifacts:
        raise ReviewRunnerError("No completed SDLC phase outputs are available for Review Code Base.")

    catalog = json.dumps(artifacts, indent=2)
    agent_definition = _read_agent_definition("review-code-base")
    skill = _read_skill("review-code-base")
    instructions = "\n\n".join([
        agent_definition,
        f"Skill methodology:\n{skill}" if skill else "",
        "AVAILABLE ARTIFACT CATALOGUE (metadata only; retrieve content with tools when needed):\n" + catalog,
        "The generated phase artifacts are intermediate analysis, not authoritative evidence. The cloned repository is the authoritative source for material verification.",
        "Do not perform repository-wide discovery before using the artifact catalogue. Start by identifying which available artifacts are relevant. Retrieve them selectively. Use repository search/read tools only for targeted verification or unresolved questions.",
    ])

    client = AsyncOpenAI(base_url=base_url, api_key=api_key.strip())
    agent = Agent(name="Review Code Base", instructions=instructions, model=OpenAIChatCompletionsModel(model=model.strip(), openai_client=client), tools=_build_review_tools(repository, output_run_dir))
    diagnostics = ReviewDiagnostics(uuid.uuid4().hex[:12])
    if run_control and run_control.is_cancelled():
        raise RunCancelled("Analysis stopped by the user.")
    result = await Runner.run(agent, "Review the available reverse-engineering artifacts and produce the cross-phase Review Code Base report.", hooks=diagnostics, max_turns=settings.phase_agent_max_turns)
    output = str(result.final_output or "").strip()
    if not output:
        raise ReviewRunnerError("Review Code Base completed but returned no final output.")
    actual_model = model.strip()
    raw_responses = getattr(result, "raw_responses", None) or []
    for raw_response in reversed(raw_responses):
        response = getattr(raw_response, "response", raw_response)
        response_model = getattr(response, "model", None)
        if response_model:
            actual_model = str(response_model)
            break
    return output, actual_model, diagnostics.turns, diagnostics.tool_calls


def run_review_code_base(*, repo_url: str, output_run_dir: Path, provider: str, model: str, api_key: str, run_control: Optional[RunControl] = None) -> dict:
    if not repo_url or not repo_url.strip():
        raise ReviewRunnerError("Repository URL is required.")
    if not api_key or not api_key.strip():
        raise ReviewRunnerError("An API key is required for Review Code Base.")
    if not _artifact_catalog(output_run_dir):
        raise ReviewRunnerError("No completed SDLC phase outputs are available for Review Code Base.")

    if run_control:
        run_control.phase_started("review-code-base")
    try:
        with tempfile.TemporaryDirectory(prefix="review-code-base-") as tmp:
            repository = clone_repository(repo_url, Path(tmp))
            raw_result, actual_model, turns, tool_calls = asyncio.run(_run_review(repository=repository, output_run_dir=output_run_dir, provider=provider, model=model, api_key=api_key, run_control=run_control))
        review_dir = output_run_dir / "review-code-base"
        review_dir.mkdir(parents=True, exist_ok=True)
        (review_dir / "agent-output.md").write_text(raw_result, encoding="utf-8")
        rendered = render_analysis(phase="review-code-base", analysis=raw_result, provider=provider, model=actual_model, api_key=api_key, run_control=run_control)
        raw_path = review_dir / "raw.md"
        raw_path.write_text(f"---\nmodel: {actual_model}\n---\n\n{rendered}\n", encoding="utf-8")
        provenance = {"model": actual_model, "turns": turns, "tool_calls": tool_calls, "source_artifacts": [item["phase"] for item in _artifact_catalog(output_run_dir)]}
        (review_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
        if run_control: run_control.phase_completed("review-code-base")
        return {"raw_path": str(raw_path), "content": rendered, "provenance": provenance}
    except Exception:
        if run_control and not run_control.is_cancelled():
            run_control.phase_failed({"phase": "review-code-base", "phase_name": "Review Code Base", "error_type": "ReviewRunnerError", "error": "Review Code Base execution failed."})
        raise
