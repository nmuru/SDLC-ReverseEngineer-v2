"""Phase-specific deterministic evidence packages.

Collectors aggregate programmatically obtainable repository facts. They deliberately expose
candidates and relationships rather than making architectural or design conclusions.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from .repository_intelligence import RepositoryIntelligence, collect_repository_intelligence


def _by_path(intelligence: RepositoryIntelligence):
    return {item.path: item for item in intelligence.source_files}


def _topology(intelligence: RepositoryIntelligence, limit: int = 40) -> list[str]:
    counts = Counter(path.split("/", 1)[0] for path in intelligence.files)
    return [f"- {name}/: {count} tracked files" for name, count in counts.most_common(limit)]


def _dependency_edges(intelligence: RepositoryIntelligence, limit: int = 120) -> list[str]:
    edges = []
    for item in intelligence.source_files:
        for imported in item.imports[:100]:
            if imported.startswith("."):
                edges.append(f"- {item.path} -> {imported}")
    return edges[:limit]


def _signal_files(intelligence: RepositoryIntelligence, signals: set[str], limit: int = 80) -> list[str]:
    # Signals are inferred from source structures below without asserting a pattern.
    patterns = {
        "context": ("context", "provider"),
        "adapter": ("adapter",),
        "repository": ("repository",),
        "factory": ("factory",),
        "observer": ("subscribe", "listener", "event", "observer"),
        "state": ("store", "context", "provider", "redux", "zustand"),
        "cache": ("cache", "revalidate"),
        "integration": ("client", "sdk", "api", "graphql", "stripe", "shopify", "supabase", "firebase"),
    }
    selected = []
    for item in intelligence.source_files:
        haystack = (item.path + " " + " ".join(item.imports) + " " + " ".join(item.exports)).lower()
        if any(any(token in haystack for token in patterns[name]) for name in signals if name in patterns):
            selected.append(item.path)
    return selected[:limit]


def _architecture_evidence(intelligence: RepositoryIntelligence) -> list[str]:
    lines = ["ARCHITECTURE EVIDENCE COLLECTED PROGRAMMATICALLY", "", "Runtime and framework evidence:"]
    lines.extend(f"- {technology}" for technology in intelligence.technologies) or lines.append("- none detected")
    lines.extend(["", "Application topology:", *_topology(intelligence)])
    lines.extend(["", "Configuration and deployment evidence:"])
    lines.extend(f"- {path}" for path in (intelligence.config_files + intelligence.ci_files)[:80]) or lines.append("- none detected")
    lines.extend(["", "Routes and entry points:"])
    lines.extend(f"- {path}" for path in (intelligence.api_routes + intelligence.page_files)[:120]) or lines.append("- none detected")
    lines.extend(["", "External integration candidates:"])
    lines.extend(f"- {path}" for path in _signal_files(intelligence, {"integration"}))
    lines.extend(f"- {path}" for path in intelligence.integration_files if path not in _signal_files(intelligence, {"integration"}))
    if lines[-1] == "External integration candidates:": lines.append("- none detected")
    lines.extend(["", "State-management candidates:"])
    state = _signal_files(intelligence, {"state"})
    lines.extend(f"- {path}" for path in state) or lines.append("- none detected")
    lines.extend(["", "Caching and revalidation candidates:"])
    cache = _signal_files(intelligence, {"cache"})
    lines.extend(f"- {path}" for path in cache) or lines.append("- none detected")
    lines.extend(["", "Environment-variable evidence:"])
    lines.extend(f"- {name}" for name in intelligence.env_variables[:100]) or lines.append("- none detected")
    lines.extend(["", "Module dependency evidence:", *_dependency_edges(intelligence)])
    return lines


def _pattern_evidence(intelligence: RepositoryIntelligence) -> list[str]:
    groups = {"Provider/Context candidates": {"context"}, "Adapter candidates": {"adapter", "integration"}, "Repository candidates": {"repository"}, "Factory candidates": {"factory"}, "Observer/subscription candidates": {"observer"}}
    lines = ["PATTERN EVIDENCE COLLECTED PROGRAMMATICALLY"]
    for title, signals in groups.items():
        matches = _signal_files(intelligence, signals)
        lines.extend(["", title + ":"])
        lines.extend(f"- {path}" for path in matches) if matches else lines.append("- no conventional candidate detected")
    return lines


def _baseline(intelligence: RepositoryIntelligence) -> list[str]:
    return ["REPOSITORY BASELINE", f"Repository files considered: {intelligence.file_count}", f"Technologies: {', '.join(intelligence.technologies) or 'not detected'}", f"Environment variables: {', '.join(intelligence.env_variables) or 'none detected'}", f"Package scripts: {intelligence.package_scripts}"]


def _generic_evidence(intelligence: RepositoryIntelligence, phase: str) -> list[str]:
    by_directory: dict[str, list[str]] = defaultdict(list)
    for item in intelligence.source_files:
        by_directory[str(Path(item.path).parent)].append(item.path)
    lines = [f"PROGRAMMATIC EVIDENCE FOR {phase}", "", "Directory structure:", *_topology(intelligence), "", "Routes:"]
    lines.extend(f"- {path}" for path in intelligence.routes[:120]) or lines.append("- none detected")
    lines.extend(["", "Tests:"])
    lines.extend(f"- {path}" for path in intelligence.test_files[:120]) or lines.append("- none detected")
    lines.extend(["", "Dependency relationships:", *_dependency_edges(intelligence)])
    return lines


def build_phase_intelligence(intelligence: RepositoryIntelligence, phase: str) -> str:
    lines = [f"PHASE-SPECIFIC DETERMINISTIC INTELLIGENCE: {phase}", "The following evidence was collected programmatically before the LLM started. Interpret and validate it; do not repeat repository-wide discovery merely to rediscover these facts.", "", *_baseline(intelligence), ""]
    if phase == "technology-architecture": lines.extend(_architecture_evidence(intelligence))
    elif phase == "design-pattern": lines.extend(_pattern_evidence(intelligence))
    else: lines.extend(_generic_evidence(intelligence, phase))
    if phase == "future-directions":
        markers = [f"- {item.path}: {', '.join(item.markers)}" for item in intelligence.source_files if item.markers]
        lines.extend(["", "Explicit maintenance and technical-debt markers:", *(markers[:100] or ["- none detected"])])
    return "\n".join(lines)


def collect_phase_intelligence(repository: Path, phase: str, intelligence: RepositoryIntelligence | None = None) -> tuple[RepositoryIntelligence, str]:
    intelligence = intelligence or collect_repository_intelligence(repository)
    return intelligence, build_phase_intelligence(intelligence, phase)
