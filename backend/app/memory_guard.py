"""Memory capacity protection for long-running analysis work."""

from __future__ import annotations

import os
from pathlib import Path

import psutil


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


def ensure_memory_available(min_available_mb: int, context: str = "analysis") -> None:
    available, used, limit = memory_snapshot()
    if available < min_available_mb * 1024 * 1024:
        raise MemoryCapacityError(
            f"Temporary memory capacity is too low to start or continue {context}. "
            f"Available memory: {available / 1024 / 1024:.0f} MB; "
            f"required reserve: {min_available_mb} MB."
        )


def memory_pressure(critical_available_mb: int) -> bool:
    available, _, _ = memory_snapshot()
    return available < critical_available_mb * 1024 * 1024
