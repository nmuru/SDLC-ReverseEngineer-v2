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

from agents import Agent, Runner, RunHooks, function_tool, set_tracing_export_api_key
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from .config import settings
from .run_control import RunCancelled, RunControl

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_SOURCE = PROJECT_ROOT / ".agents" / "agents"
SKILLS_SOURCE = PROJECT_ROOT / ".agents" / "skills"

if settings.openai_tracing_api_key:
    set_tracing_export_api_key(settings.openai_tracing_api_key)
    logger.info("OpenAI Agents tracing export is enabled.")


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
