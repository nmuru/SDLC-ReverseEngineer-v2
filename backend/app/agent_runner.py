"""Claude Agent SDK phase runner for repository reverse engineering."""

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENCODE_SKILLS_SOURCE = PROJECT_ROOT / ".opencode" / "skills"


class AgentRunnerError(RuntimeError):
    """Raised when a repository-analysis phase cannot be completed."""


def _clone_repository(repo_url: str, workspace: Path) -> Path:
    """Clone the target repository into an isolated temporary workspace."""
    repository = workspace / "target-repository"
    if repository.exists():
        shutil.rmtree(repository, ignore_errors=True)

    result = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url.strip(), str(repository)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise AgentRunnerError(
            "Could not clone the target repository: " + result.stderr.strip()[:2000]
        )
    return repository


def _install_project_skills(repository: Path) -> None:
    """Expose the existing phase skills through the Claude Agent SDK layout."""
    if not OPENCODE_SKILLS_SOURCE.exists():
        return

    destination = repository / ".claude" / "skills"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(OPENCODE_SKILLS_SOURCE, destination, dirs_exist_ok=True)


async def _run_agent(
    *,
    phase: str,
    phase_name: str,
    repository: Path,
    model: str,
    api_key: str,
    previous_output: Optional[str],
) -> str:
    handoff_context = ""
    if previous_output:
        handoff_context = (
            "\n\nPrevious phase output is provided below as supporting context. "
            "Verify important claims against the repository rather than accepting it blindly.\n\n"
            + previous_output
        )

    prompt = f"""
Perform the \"{phase_name}\" phase of the repository reverse-engineering workflow.

This is a read-only documentation task. The current working directory is a clone
of the target repository. Inspect the repository directly using the available
read-only tools. Do not modify repository files.

Load and follow the phase-specific skill named \"{phase}\" before beginning the
analysis. The skill defines the investigation workflow and documentation output
requirements.

Treat repository evidence as authoritative. Complete the full phase analysis.

FINAL OUTPUT:
Return only the complete final SDLC documentation for this phase as normal
Markdown. Do not wrap the documentation in JSON and do not add a response
envelope. Mermaid diagrams, tables, lists, headings, and code blocks are allowed
when appropriate.
""".strip() + handoff_context

    options = ClaudeAgentOptions(
        model=model.strip(),
        cwd=repository,
        setting_sources=["project"],
        skills=[phase],
        allowed_tools=["Read", "Glob", "Grep", "Bash"],
        disallowed_tools=["Write", "Edit"],
        permission_mode="bypassPermissions",
        env={
            "ANTHROPIC_API_KEY": api_key.strip(),
            "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        },
    )

    final_result: Optional[str] = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if message.subtype != "success":
                raise AgentRunnerError(
                    f"Claude Agent SDK failed phase '{phase}' with result "
                    f"subtype '{message.subtype}'."
                )
            final_result = message.result

    if not final_result or not final_result.strip():
        raise AgentRunnerError(
            f"Claude Agent SDK completed phase '{phase}' but returned no final output."
        )

    return final_result.strip()


def run_phase_agent(
    phase: str,
    phase_name: str,
    workspace: Path,
    repo_url: str,
    previous_output: Optional[str] = None,
    provider: str = "anthropic",
    model: str = "claude-sonnet-5",
    api_key: Optional[str] = None,
) -> str:
    """Run one repository-analysis phase using the Claude Agent SDK."""
    if provider.strip().lower() != "anthropic":
        raise AgentRunnerError(
            f"Unsupported provider '{provider}'. This backend currently uses the Claude Agent SDK and supports Anthropic API authentication."
        )
    if not api_key or not api_key.strip():
        raise AgentRunnerError("An Anthropic API key is required.")

    workspace.mkdir(parents=True, exist_ok=True)
    repository = _clone_repository(repo_url, workspace)
    _install_project_skills(repository)

    try:
        return asyncio.run(
            _run_agent(
                phase=phase,
                phase_name=phase_name,
                repository=repository,
                model=model,
                api_key=api_key,
                previous_output=previous_output,
            )
        )
    except AgentRunnerError:
        raise
    except Exception as exc:
        logger.exception("Claude Agent SDK failed during phase %s", phase)
        raise AgentRunnerError(
            f"Claude Agent SDK failed during phase '{phase}': {exc}"
        ) from exc
