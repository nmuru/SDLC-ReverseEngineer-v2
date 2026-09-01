"""Repository analysis orchestration."""

import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional

from .agent_runner import run_phase_agent
from .config import settings
from .exporter import create_download_package
from .renderer import render_analysis
from .resource_diagnostics import ResourceDiagnostics

PHASES = [
    ("business-purpose", "Business Purpose"),
    ("features", "Features"),
    ("business-requirements", "Business Requirements"),
    ("software-requirements", "Software Requirements"),
    ("technology-architecture", "Technology Architecture"),
    ("design-pattern", "Design Pattern"),
    ("high-level-design", "High-Level Design"),
    ("low-level-design", "Low-Level Design"),
    ("implementation-detail", "Implementation Detail"),
    ("testing-harness", "Testing Harness"),
    ("future-directions", "Future Directions"),
]

PhaseCompleteCallback = Callable[[dict], None]


def _run_single_phase(
    phase_key: str,
    phase_name: str,
    workspace: Path,
    repo_url: str,
    output_run_dir: Path,
    run_id: str,
    provider: str,
    model: str,
    api_key: str,
    diagnostics: Optional[ResourceDiagnostics] = None,
    batch_index: Optional[int] = None,
) -> dict:
    phase_workspace = workspace / phase_key
    phase_workspace.mkdir(parents=True, exist_ok=True)
    if diagnostics:
        diagnostics.phase_start(phase_key, phase_name, batch_index=batch_index)
    try:
        raw_result = run_phase_agent(
            phase=phase_key,
            phase_name=phase_name,
            workspace=phase_workspace,
            repo_url=repo_url,
            provider=provider,
            model=model,
            api_key=api_key,
        )
        if not raw_result.strip():
            raise RuntimeError(f"OpenAI Agents SDK returned an empty result for phase '{phase_key}'.")
        phase_output_dir = output_run_dir / phase_key
        phase_output_dir.mkdir(parents=True, exist_ok=True)
        (phase_output_dir / "agent-output.md").write_text(raw_result, encoding="utf-8")
        rendered_result = render_analysis(
            phase=phase_key,
            analysis=raw_result,
            provider=provider,
            model=model,
            api_key=api_key,
        )
        if not rendered_result.strip():
            raise RuntimeError(f"Renderer returned an empty result for phase '{phase_key}'.")
        raw_path = phase_output_dir / "raw.md"
        raw_path.write_text(rendered_result, encoding="utf-8")
        if diagnostics:
            diagnostics.phase_end(phase_key, phase_name, batch_index=batch_index, status="completed")
        return {
            "phase": phase_key,
            "phase_name": phase_name,
            "raw_analysis": rendered_result,
            "raw_path": str(raw_path),
            "run_id": run_id,
        }
    except Exception:
        if diagnostics:
            diagnostics.phase_end(phase_key, phase_name, batch_index=batch_index, status="failed")
        raise


def _phase_failure(phase_key: str, phase_name: str, exc: Exception) -> dict:
    return {
        "phase": phase_key,
        "phase_name": phase_name,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }


def _run_batch(
    batch: list[tuple[str, str]],
    workspace: Path,
    repo_url: str,
    output_run_dir: Path,
    run_id: str,
    on_phase_complete: Optional[PhaseCompleteCallback] = None,
    provider: str = "openrouter",
    model: str = "openrouter/free",
    api_key: str = "",
    diagnostics: Optional[ResourceDiagnostics] = None,
    batch_index: Optional[int] = None,
) -> tuple[dict, list[dict]]:
    batch_results: dict[str, dict] = {}
    batch_failures: list[dict] = []
    phase_by_future = {}

    with ThreadPoolExecutor(max_workers=len(batch)) as executor:
        for key, name in batch:
            future = executor.submit(
                _run_single_phase,
                key,
                name,
                workspace,
                repo_url,
                output_run_dir,
                run_id,
                provider,
                model,
                api_key,
                diagnostics,
                batch_index,
            )
            phase_by_future[future] = (key, name)

        for future in as_completed(phase_by_future):
            key, name = phase_by_future[future]
            try:
                result = future.result()
                batch_results[result["phase"]] = result
                if on_phase_complete:
                    on_phase_complete(result)
            except Exception as exc:
                batch_failures.append(_phase_failure(key, name, exc))

    return batch_results, batch_failures


def analyze_repository(
    repo_url: str,
    phases_per_batch: int = settings.phases_per_batch,
    number_of_batches: Optional[int] = None,
    batch_mode: str = settings.batch_mode,
    on_phase_complete: Optional[PhaseCompleteCallback] = None,
    selected_phases: Optional[list[str]] = None,
    work_id: Optional[str] = None,
    provider: str = "openrouter",
    model: str = "openrouter/free",
    api_key: Optional[str] = None,
) -> dict:
    if not repo_url or not repo_url.strip():
        raise ValueError("repo_url cannot be empty")
    provider = (provider or "").strip().lower()
    if provider not in {"openrouter", "openai"}:
        raise ValueError("This backend currently supports OpenRouter and OpenAI through the OpenAI Agents SDK")
    if not model or not model.strip():
        raise ValueError("model cannot be empty")
    if not api_key or not api_key.strip():
        raise ValueError("api_key cannot be empty")
    if phases_per_batch < 1:
        raise ValueError("phases_per_batch must be at least 1")
    if batch_mode not in {"parallel", "sequence"}:
        raise ValueError("batch_mode must be 'parallel' or 'sequence'")

    available = {key for key, _ in PHASES}
    if selected_phases is None:
        count = number_of_batches or 1
        selected_ids = [key for key, _ in PHASES[:phases_per_batch * count]]
    else:
        if not selected_phases:
            raise ValueError("selected_phases must contain at least one phase")
        if len(set(selected_phases)) != len(selected_phases):
            raise ValueError("selected_phases must not contain duplicates")
        unknown = set(selected_phases) - available
        if unknown:
            raise ValueError("selected_phases contains unknown phases: " + ", ".join(sorted(unknown)))
        selected_ids = selected_phases

    phase_by_id = dict(PHASES)
    definitions = [(key, phase_by_id[key]) for key in selected_ids]
    batches = [definitions[i:i + phases_per_batch] for i in range(0, len(definitions), phases_per_batch)]
    run_id = work_id or uuid.uuid4().hex
    if not run_id.isalnum():
        raise ValueError("work_id must contain only letters and numbers")

    output_root = Path(settings.analysis_results_dir)
    if not output_root.is_absolute():
        output_root = Path(__file__).resolve().parents[1] / output_root
    output_run_dir = output_root / run_id
    output_run_dir.mkdir(parents=True, exist_ok=True)
    completed = {p.name for p in output_run_dir.iterdir() if p.is_dir() and (p / "raw.md").is_file()}
    duplicate = completed.intersection(selected_ids)
    if duplicate:
        raise ValueError("selected_phases already completed: " + ", ".join(sorted(duplicate)))

    diagnostics_dir = Path(settings.resource_diagnostics_dir)
    if not diagnostics_dir.is_absolute():
        diagnostics_dir = output_run_dir / diagnostics_dir
    diagnostics = ResourceDiagnostics(
        enabled=settings.resource_diagnostics_enabled,
        output_dir=diagnostics_dir,
        sample_interval_seconds=settings.resource_diagnostics_interval_seconds,
        run_id=run_id,
    )
    diagnostics.start()
    diagnostics.run_event(
        "analysis_started",
        selected_phases=selected_ids,
        phases_per_batch=phases_per_batch,
        batch_mode=batch_mode,
        batch_count=len(batches),
        provider=provider,
        model=model,
    )

    results: dict[str, dict] = {}
    failures: list[dict] = []
    try:
        with tempfile.TemporaryDirectory(prefix="reverse-engineer-") as tmp:
            workspace = Path(tmp)
            diagnostics.run_event("workspace_created", workspace=str(workspace))

            if batch_mode == "parallel":
                with ThreadPoolExecutor(max_workers=len(batches)) as executor:
                    futures = {
                        executor.submit(
                            _run_batch,
                            batch,
                            workspace,
                            repo_url,
                            output_run_dir,
                            run_id,
                            on_phase_complete,
                            provider,
                            model,
                            api_key,
                            diagnostics,
                            index,
                        ): index
                        for index, batch in enumerate(batches, start=1)
                    }
                    for future in as_completed(futures):
                        batch_results, batch_failures = future.result()
                        results.update(batch_results)
                        failures.extend(batch_failures)
            else:
                for index, batch in enumerate(batches, start=1):
                    batch_results, batch_failures = _run_batch(
                        batch,
                        workspace,
                        repo_url,
                        output_run_dir,
                        run_id,
                        on_phase_complete,
                        provider,
                        model,
                        api_key,
                        diagnostics,
                        index,
                    )
                    results.update(batch_results)
                    failures.extend(batch_failures)

        create_download_package(output_run_dir)
        diagnostics.run_event(
            "analysis_completed",
            completed_phases=list(results),
            failed_phases=[failure["phase"] for failure in failures],
        )
        return {"run_id": run_id, "results": results, "failures": failures}
    except Exception as exc:
        diagnostics.run_event("analysis_failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        diagnostics.stop()
