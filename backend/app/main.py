import asyncio
import json
import logging
import shutil
import time
from pathlib import Path
from queue import Queue
from threading import Lock, Thread
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from .agent_runner import AgentRunnerError
from .analyzer import analyze_repository
from .config import settings
from .run_control import RunCancelled, RunControl, load_persisted_run
from .schemas import AnalyzeRequest

logger = logging.getLogger(__name__)

app = FastAPI(title="ReverseEngineer-SDLC API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_run_controls: dict[str, RunControl] = {}
_run_controls_lock = Lock()


def _output_root() -> Path:
    root = Path(settings.analysis_results_dir)
    return root if root.is_absolute() else Path(__file__).resolve().parents[1] / root


def _run_dir(work_id: str) -> Path:
    if Path(work_id).name != work_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _output_root() / work_id


def _cleanup_run_dir(work_id: str) -> bool:
    run_dir = _run_dir(work_id)
    if not run_dir.exists():
        return False
    shutil.rmtree(run_dir)
    return True


def _cleanup_after_run_finishes(control: RunControl, timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if control.snapshot().get("status") in {"completed", "failed", "cancelled"}:
            try:
                _cleanup_run_dir(control.run_id)
            except OSError:
                logger.exception("Unable to clean production output for work_id=%s", control.run_id)
            return
        time.sleep(0.5)
    logger.warning("Production cleanup timed out while waiting for work_id=%s", control.run_id)


def _read_phase_result(run_id: str, phase: str) -> str | None:
    if Path(run_id).name != run_id or Path(phase).name != phase:
        return None
    path = _output_root() / run_id / phase / "raw.md"
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) == 3:
            content = parts[2]
    return content.strip()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/analysis/{work_id}/status")
def analysis_status(work_id: str) -> dict[str, Any]:
    if Path(work_id).name != work_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    with _run_controls_lock:
        control = _run_controls.get(work_id)
    state = control.snapshot() if control else load_persisted_run(_output_root() / work_id / "run-state.json")
    if state is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    completed = list(state.get("completed_phases", []))
    results = {phase: content for phase in completed if (content := _read_phase_result(work_id, phase)) is not None}
    return {**state, "results": results}


@app.post("/api/analysis/{work_id}/stop")
def stop_analysis(work_id: str) -> dict[str, Any]:
    if Path(work_id).name != work_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    with _run_controls_lock:
        control = _run_controls.get(work_id)
    if control is None:
        state = load_persisted_run(_output_root() / work_id / "run-state.json")
        if state is None:
            raise HTTPException(status_code=404, detail="Analysis not found")
        if state.get("status") in {"completed", "failed", "cancelled"}:
            return state
        raise HTTPException(status_code=409, detail="The analysis is no longer attached to this server process and cannot be stopped here.")
    control.cancel()
    return control.snapshot()


@app.post("/api/analysis/{work_id}/close")
def close_analysis(work_id: str) -> dict[str, Any]:
    """Close a UI workspace; production mode removes its server-side output."""
    run_dir = _run_dir(work_id)
    with _run_controls_lock:
        control = _run_controls.get(work_id)

    if settings.runtime_mode.lower() != "production":
        return {"run_id": work_id, "runtime_mode": settings.runtime_mode, "retained": True, "cleanup_scheduled": False}

    if control is not None and control.snapshot().get("status") in {"running", "cancelling"}:
        control.cancel()
        Thread(target=_cleanup_after_run_finishes, args=(control,), daemon=True).start()
        return {"run_id": work_id, "runtime_mode": settings.runtime_mode, "retained": False, "cleanup_scheduled": True}

    deleted = False
    if run_dir.exists():
        try:
            deleted = _cleanup_run_dir(work_id)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Unable to clean analysis output: {exc}") from exc
    return {"run_id": work_id, "runtime_mode": settings.runtime_mode, "retained": False, "cleanup_scheduled": False, "deleted": deleted}


@app.get("/api/analysis/{work_id}/download")
def download_analysis(work_id: str) -> FileResponse:
    if Path(work_id).name != work_id:
        raise HTTPException(status_code=404, detail="Analysis download not found")
    zip_path = _output_root() / work_id / "sdlc-documentation.zip"
    if not zip_path.is_file():
        raise HTTPException(status_code=404, detail="Analysis download not found")
    return FileResponse(zip_path, media_type="application/zip", filename="sdlc-documentation.zip")


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> StreamingResponse:
    """Run the analysis pipeline and stream completed phases and actionable failures."""
    repo_url = str(request.repo_url)
    event_queue: Queue[dict[str, Any]] = Queue()
    run_id = request.work_id or ""

    if run_id:
        with _run_controls_lock:
            existing = _run_controls.get(run_id)
        if existing and existing.snapshot().get("status") in {"running", "cancelling"}:
            raise HTTPException(status_code=409, detail="An analysis with this work ID is already running.")

    def on_phase_complete(phase_result: dict) -> None:
        event_queue.put({
            "type": "phase_completed",
            "phase": phase_result["phase"],
            "phase_name": phase_result["phase_name"],
            "raw_analysis": phase_result["raw_analysis"],
            "raw_path": phase_result["raw_path"],
            "run_id": phase_result["run_id"],
            "provenance": phase_result.get("provenance"),
        })

    def run_analysis() -> None:
        control: RunControl | None = None
        try:
            resolved_run_id = request.work_id
            if not resolved_run_id:
                import uuid
                resolved_run_id = uuid.uuid4().hex
            output_run_dir = _output_root() / resolved_run_id
            output_run_dir.mkdir(parents=True, exist_ok=True)
            control = RunControl(resolved_run_id, output_run_dir / "run-state.json")
            control.initialize(repo_url=repo_url, selected_phases=request.selected_phases)
            with _run_controls_lock:
                _run_controls[resolved_run_id] = control

            results = analyze_repository(
                repo_url,
                phases_per_batch=settings.phases_per_batch,
                batch_mode=settings.batch_mode,
                selected_phases=request.selected_phases,
                work_id=resolved_run_id,
                on_phase_complete=on_phase_complete,
                provider=request.provider,
                model=request.model,
                api_key=request.api_key,
                run_control=control,
            )
            if control.is_cancelled():
                control.finish("cancelled")
                event_queue.put({
                    "type": "analysis_cancelled",
                    "repo_url": repo_url,
                    "run_id": resolved_run_id,
                    "completed_phases": list(results["results"].keys()),
                    "failed_phases": results.get("failures", []),
                })
            else:
                control.finish("completed")
                event_queue.put({
                    "type": "analysis_completed",
                    "repo_url": repo_url,
                    "run_id": results["run_id"],
                    "completed_phases": list(results["results"].keys()),
                    "failed_phases": results.get("failures", []),
                })
        except RunCancelled:
            if control:
                control.finish("cancelled")
                event_queue.put({"type": "analysis_cancelled", "repo_url": repo_url, "run_id": control.run_id, "completed_phases": list(control.snapshot()["completed_phases"]), "failed_phases": control.snapshot()["failures"]})
        except (AgentRunnerError, ValueError) as exc:
            if control:
                control.finish("failed")
            event_queue.put({"type": "analysis_failed", "repo_url": repo_url, "run_id": control.run_id if control else resolved_run_id, "error": str(exc)})
        except Exception as exc:
            if control:
                control.finish("failed")
            logger.exception("Unexpected analysis failure: repo_url=%s", repo_url)
            event_queue.put({
                "type": "analysis_failed",
                "repo_url": repo_url,
                "run_id": control.run_id if control else resolved_run_id,
                "error": f"Analysis failed due to an unexpected backend error: {type(exc).__name__}: {exc}",
            })

    Thread(target=run_analysis, daemon=True).start()

    async def event_stream():
        while True:
            event = await asyncio.to_thread(event_queue.get)
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event["type"] in {"analysis_completed", "analysis_failed", "analysis_cancelled"}:
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
