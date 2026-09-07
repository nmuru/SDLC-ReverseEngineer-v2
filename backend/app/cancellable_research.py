"""Run semantic research in killable child processes.

Semantic research uses direct OpenAI/OpenRouter HTTP requests. Keeping each research
request in its own child process gives the run controller a hard OS-level cancellation
boundary: terminating the child also terminates its in-flight HTTP request instead of
leaving an asyncio/httpx task running after the UI workspace is closed.
"""
from __future__ import annotations

import multiprocessing as mp
import traceback
from pathlib import Path
from queue import Empty
from typing import Any, Callable

from .run_control import RunCancelled, RunControl


def _research_worker(kind: str, kwargs: dict[str, Any], result_queue: Any) -> None:
    """Execute one semantic research request inside an isolated process."""
    try:
        from .semantic_research import run_phase_research, run_repository_research

        function: Callable[..., str]
        if kind == "repository":
            function = run_repository_research
        elif kind == "phase":
            function = run_phase_research
        else:
            raise ValueError(f"Unsupported semantic research kind: {kind}")

        result = function(**kwargs)
        result_queue.put({"ok": True, "result": result})
    except BaseException as exc:
        result_queue.put({"ok": False, "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})


def _run_cancellable(kind: str, kwargs: dict[str, Any], run_control: RunControl | None) -> str:
    if run_control and run_control.is_cancelled():
        raise RunCancelled("Analysis stopped by the user.")

    context = mp.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(target=_research_worker, args=(kind, kwargs, result_queue), daemon=True)
    process.start()
    payload: dict[str, Any] | None = None
    try:
        # Drain the queue while the worker is alive. Waiting for process.join() before
        # reading the Queue can deadlock when the worker has produced a result but its
        # multiprocessing feeder thread is still flushing that result to the parent.
        while process.is_alive():
            if run_control and run_control.is_cancelled():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=2)
                raise RunCancelled("Analysis stopped by the user.")
            try:
                payload = result_queue.get_nowait()
                break
            except Empty:
                process.join(timeout=0.1)

        if payload is None:
            if run_control and run_control.is_cancelled():
                raise RunCancelled("Analysis stopped by the user.")
            try:
                payload = result_queue.get(timeout=5)
            except Empty as exc:
                raise RuntimeError(f"Semantic research worker exited without a result (kind={kind}, exit_code={process.exitcode}).") from exc

        if payload.get("ok"):
            return str(payload.get("result") or "")
        raise RuntimeError(f"{payload.get('error_type', 'SemanticResearchError')}: {payload.get('error', 'semantic research failed')}")
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
        try:
            result_queue.close()
            result_queue.join_thread()
        except (AttributeError, OSError):
            pass


def run_repository_research(*, intelligence: Any, repository: Path, provider: str, model: str, api_key: str, run_control: RunControl | None = None) -> str:
    return _run_cancellable("repository", {"intelligence": intelligence, "repository": repository, "provider": provider, "model": model, "api_key": api_key}, run_control)


def run_phase_research(*, phase: str, phase_intelligence: str, repository_research: str, repository: Path, provider: str, model: str, api_key: str, run_control: RunControl | None = None) -> str:
    return _run_cancellable("phase", {"phase": phase, "phase_intelligence": phase_intelligence, "repository": repository, "provider": provider, "model": model, "api_key": api_key, "repository_research": repository_research}, run_control)
