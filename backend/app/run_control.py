"""Per-analysis run state and cancellation controls."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Optional


class RunControl:
    def __init__(self, run_id: str, state_path: Path) -> None:
        self.run_id = run_id
        self.state_path = state_path
        self.cancel_event = threading.Event()
        self._lock = threading.Lock()
        self.status = "running"
        self.repo_url = ""
        self.selected_phases: list[str] = []
        self.completed_phases: list[str] = []
        self.failures: list[dict[str, Any]] = []
        self.active_phase: Optional[str] = None

    def initialize(self, *, repo_url: str, selected_phases: list[str]) -> None:
        self.repo_url = repo_url
        self.selected_phases = list(selected_phases)
        self.persist()

    def cancel(self) -> bool:
        with self._lock:
            if self.status in {"completed", "failed", "cancelled"}:
                return False
            self.status = "cancelling"
            self.cancel_event.set()
        self.persist()
        return True

    def phase_started(self, phase: str) -> None:
        with self._lock:
            self.active_phase = phase
        self.persist()

    def phase_completed(self, phase: str) -> None:
        with self._lock:
            if phase not in self.completed_phases:
                self.completed_phases.append(phase)
            self.active_phase = None
        self.persist()

    def phase_failed(self, failure: dict[str, Any]) -> None:
        with self._lock:
            self.failures = [item for item in self.failures if item.get("phase") != failure.get("phase")]
            self.failures.append(failure)
            self.active_phase = None
        self.persist()

    def finish(self, status: str) -> None:
        with self._lock:
            self.status = status
            self.active_phase = None
        self.persist()

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "run_id": self.run_id,
                "status": self.status,
                "repo_url": self.repo_url,
                "selected_phases": list(self.selected_phases),
                "completed_phases": list(self.completed_phases),
                "failures": list(self.failures),
                "active_phase": self.active_phase,
            }

    def persist(self) -> None:
        payload = self.snapshot()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.state_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_path.replace(self.state_path)


class RunCancelled(Exception):
    """Raised when the user cancels an analysis run."""


def load_persisted_run(state_path: Path) -> dict[str, Any] | None:
    if not state_path.is_file():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
