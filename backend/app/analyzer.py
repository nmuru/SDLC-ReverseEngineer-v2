"""Repository analysis orchestration."""

import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional

from .agent_runner import clone_repository, github_repository_size_bytes, repository_size_bytes, run_phase_agent
from .config import settings
from .exporter import create_download_package
from .phase_intelligence import build_phase_intelligence
from .renderer import render_analysis
from .repository_intelligence import RepositoryIntelligence, collect_repository_intelligence
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


def _repository_size_limit_error() -> ValueError:
    return ValueError(
        f"This app does not support repositories larger than {settings.max_repository_size_mb} MB. "
        "We hope to enhance support for larger repositories later."
    )


def _run_single_phase(phase_key: str, phase_name: str, repository: Path, phase_intelligence: str, output_run_dir: Path, run_id: str, provider: str, model: str, api_key: str, diagnostics: Optional[ResourceDiagnostics] = None, batch_index: Optional[int] = None) -> dict:
    if diagnostics:
        diagnostics.phase_start(phase_key, phase_name, batch_index=batch_index)
    try:
        raw_result = run_phase_agent(
            phase=phase_key,
            phase_name=phase_name,
            repository=repository,
            phase_intelligence=phase_intelligence,
            provider=provider,
            model=model,
            api_key=api_key,
        )
        if not raw_result.strip():
            raise RuntimeError(f"OpenAI Agents SDK returned an empty result for phase '{phase_key}'.")
        phase_output_dir = output_run_dir / phase_key
        phase_output_dir.mkdir(parents=True, exist_ok=True)
        (phase_output_dir / "agent-output.md").write_text(raw_result, encoding="utf-8")
        rendered_result = render_analysis(phase=phase_key, analysis=raw_result, provider=provider, model=model, api_key=api_key)
        if not rendered_result.strip():
            raise RuntimeError(f"Renderer returned an empty result for phase '{phase_key}'.")
        raw_path = phase_output_dir / "raw.md"
        raw_path.write_text(rendered_result, encoding="utf-8")
        if diagnostics:
            diagnostics.phase_end(phase_key, phase_name, batch_index=batch_index, status="completed")
        return {"phase": phase_key, "phase_name": phase_name, "raw_analysis": rendered_result, "raw_path": str(raw_path), "run_id": run_id}
    except Exception:
        if diagnostics:
            diagnostics.phase_end(phase_key, phase_name, batch_index=batch_index, status="failed")
        raise


def _phase_failure(phase_key: str, phase_name: str, exc: Exception) -> dict:
    return {"phase": phase_key, "phase_name": phase_name, "error_type": type(exc).__name__, "error": str(exc)}


def _run_batch(batch: list[tuple[str, str]], repository: Path, phase_packages: dict[str, str], output_run_dir: Path, run_id: str, on_phase_complete: Optional[PhaseCompleteCallback] = None, provider: str = "openrouter", model: str = "openrouter/free", api_key: str = "", diagnostics: Optional[ResourceDiagnostics] = None, batch_index: Optional[int] = None) -> tuple[dict, list[dict]]:
    batch_results: dict[str, dict] = {}
    batch_failures: list[dict] = []
    phase_by_future = {}
    with ThreadPoolExecutor(max_workers=len(batch)) as executor:
        for key, name in batch:
            future = executor.submit(_run_single_phase, key, name, repository, phase_packages[key], output_run_dir, run_id, provider, model, api_key, diagnostics, batch_index)
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


def analyze_repository(repo_url: str, phases_per_batch: int = settings.phases_per_batch, number_of_batches: Optional[int] = None, batch_mode: str = settings.batch_mode, on_phase_complete: Optional[PhaseCompleteCallback] = None, selected_phases: Optional[list[str]] = None, work_id: Optional[str] = None, provider: str = "openrouter", model: str = "openrouter/free", api_key: Optional[str] = None) -> dict:
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
    diagnostics_dir = Path(settings.resource_diagnostics_dir)
    if not diagnostics_dir.is_absolute():
        diagnostics_dir = output_run_dir / diagnostics_dir
    diagnostics = ResourceDiagnostics(enabled=settings.resource_diagnostics_enabled, output_dir=diagnostics_dir, sample_interval_seconds=settings.resource_diagnostics_interval_seconds, run_id=run_id)
    diagnostics.start()
    diagnostics.run_event("analysis_started", selected_phases=selected_ids, phases_per_batch=phases_per_batch, batch_mode=batch_mode, batch_count=len(batches), provider=provider, model=model)

    results: dict[str, dict] = {}
    failures: list[dict] = []
    try:
        max_bytes = settings.max_repository_size_mb * 1024 * 1024
        github_size_bytes = github_repository_size_bytes(repo_url)
        if github_size_bytes is not None:
            diagnostics.run_event("repository_size_checked_before_clone", repository_size_bytes=github_size_bytes)
            if github_size_bytes > max_bytes:
                raise _repository_size_limit_error()

        with tempfile.TemporaryDirectory(prefix="reverse-engineer-") as tmp:
            workspace = Path(tmp)
            diagnostics.run_event("workspace_created", workspace=str(workspace))
            repository = clone_repository(repo_url, workspace)
            size_bytes = repository_size_bytes(repository)
            if size_bytes > max_bytes:
                raise _repository_size_limit_error()
            diagnostics.run_event("repository_cloned", repository=str(repository), repository_size_bytes=size_bytes)
            intelligence: RepositoryIntelligence = collect_repository_intelligence(repository)
            diagnostics.run_event("repository_intelligence_collected", files_considered=intelligence.file_count)
            phase_packages = {key: build_phase_intelligence(intelligence, key) for key in selected_ids}

            if batch_mode == "parallel":
                with ThreadPoolExecutor(max_workers=len(batches)) as executor:
                    futures = {executor.submit(_run_batch, batch, repository, phase_packages, output_run_dir, run_id, on_phase_complete, provider, model, api_key, diagnostics, index): index for index, batch in enumerate(batches, start=1)}
                    for future in as_completed(futures):
                        batch_results, batch_failures = future.result()
                        results.update(batch_results)
                        failures.extend(batch_failures)
            else:
                for index, batch in enumerate(batches, start=1):
                    batch_results, batch_failures = _run_batch(batch, repository, phase_packages, output_run_dir, run_id, on_phase_complete, provider, model, api_key, diagnostics, index)
                    results.update(batch_results)
                    failures.extend(batch_failures)

        create_download_package(output_run_dir)
        diagnostics.run_event("analysis_completed", completed_phases=list(results), failed_phases=[failure["phase"] for failure in failures])
        return {"run_id": run_id, "results": results, "failures": failures}
    except Exception as exc:
        diagnostics.run_event("analysis_failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        diagnostics.stop()
