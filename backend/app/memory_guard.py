"""Memory capacity protection for long-running analysis work."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


class MemoryCapacityError(RuntimeError):
    """Raised when the service should not start or continue analysis."""

    code = "MEMORY_CAPACITY"
    user_message = "Please try again later due to temporary backend memory limitations."


def _cgroup_memory() -> tuple[int | None, int | None]:
    """Return (limit, current) bytes when a Linux cgroup memory limit is visible."""
    candidates = [
        (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory.current")),
        (Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"), Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")),
    ]
    for limit_path, current_path in candidates:
        try:
            raw_limit = limit_path.read_text(encoding="utf-8").strip()
            raw_current = current_path.read_text(encoding="utf-8").strip()
            if raw_limit == "max":
                continue
            limit = int(raw_limit)
            current = int(raw_current)
            if limit > 0 and current >= 0:
                return limit, current
        except (OSError, ValueError):
            continue
    return None, None


def memory_snapshot() -> tuple[int, int, int | None]:
    """Return (available, used, limit) bytes using the tightest visible limit."""
    virtual = psutil.virtual_memory()
    available = int(virtual.available)
    used = int(virtual.total - virtual.available)
    limit, current = _cgroup_memory()
    if limit is not None and current is not None:
        available = max(0, limit - current)
        used = current
    return available, used, limit


def _safe_reserve_bytes(limit: int | None, minimum_mb: int = 256) -> int:
    """Keep a meaningful reserve, including on small hosted containers."""
    if limit is None:
        return minimum_mb * 1024 * 1024
    return max(minimum_mb * 1024 * 1024, int(limit * 0.20))


def ensure_memory_available(min_available_mb: int = 256, context: str = "analysis") -> None:
    available, _, limit = memory_snapshot()
    required = max(min_available_mb * 1024 * 1024, _safe_reserve_bytes(limit, min_available_mb))
    if available < required:
        raise MemoryCapacityError(
            f"Temporary memory capacity is too low to start or continue {context}. "
            f"Available memory: {available / 1024 / 1024:.0f} MB; "
            f"required reserve: {required / 1024 / 1024:.0f} MB."
        )


def memory_pressure(critical_available_mb: int = 128) -> bool:
    available, used, limit = memory_snapshot()
    reserve = _safe_reserve_bytes(limit, critical_available_mb)
    percent = (used / limit * 100.0) if limit else 0.0
    return available < reserve or percent >= 92.0


class MemoryCapacityGuard:
    """Watch one analysis and request cancellation before an OOM condition."""

    def __init__(self, control, interval_seconds: float = 2.0) -> None:
        self.control = control
        self.interval_seconds = max(0.5, float(interval_seconds))
        self.triggered = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, name=f"memory-guard-{control.run_id}", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=self.interval_seconds + 1.0)

    def _watch(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            if self.control.snapshot().get("status") not in {"running", "cancelling"}:
                return
            if not memory_pressure():
                continue
            available, used, limit = memory_snapshot()
            percent = (used / limit * 100.0) if limit else 0.0
            self.triggered.set()
            logger.warning(
                "Memory capacity guard triggered; cancelling analysis work_id=%s: "
                "available=%.0f MB, used=%.0f MB, limit=%s MB, used_percent=%s",
                self.control.run_id,
                available / 1024 / 1024,
                used / 1024 / 1024,
                f"{limit / 1024 / 1024:.0f}" if limit else "unlimited",
                f"{percent:.1f}" if limit else "n/a",
            )
            self.control.cancel()
            return


def capacity_diagnostics() -> dict[str, float | int | None]:
    available, used, limit = memory_snapshot()
    return {
        "pid": os.getpid(),
        "available_mb": round(available / 1024 / 1024, 2),
        "used_mb": round(used / 1024 / 1024, 2),
        "limit_mb": round(limit / 1024 / 1024, 2) if limit else None,
        "used_percent": round((used / limit) * 100, 2) if limit else None,
    }
