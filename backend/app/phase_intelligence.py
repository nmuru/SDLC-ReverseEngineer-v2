"""Phase-specific deterministic evidence packages.

Collectors aggregate programmatically obtainable repository facts. They deliberately expose
candidates, evidence and relationships rather than making architectural or design conclusions.
"""
from __future__ import annotations

from collections import Counter

from .repository_intelligence import RepositoryIntelligence, collect_repository_intelligence


def _topology(intelligence: RepositoryIntelligence, limit: int = 40) -> list[str]:
    counts = Counter(path.split("/", 1)[0] for path in intelligence.files)
    return [f"- {name}/: {count} tracked files" for name, count in counts.most_common(limit)]


def _dependency_edges(intelligence: RepositoryIntelligence, limit: int = 160) -> list[str]:
    return [
        f"- {edge.source} -> {edge.target} (import: {edge.imported_as})"
        if edge.imported_as
        else f"- {edge.source} -> {edge.target}"
        for edge in intelligence.dependency_edges[:limit]
    ]


def _signal_files(intelligence: RepositoryIntelligence, signals: set[str], limit: int = 80) -> list[str]:
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
    selected: list[str] = []
    for item in intelligence.source_files:
        haystack = (
            item.path + " " + " ".join(item.imports) + " " + " ".join(item.exports)
            + " " + " ".join(sum(item.symbols.values(), []))
        ).lower()
        if any(any(token in haystack for token in patterns[name]) for name in signals if name in patterns):
            selected.append(item.path)
    return selected[:limit]


def _technology_evidence(intelligence: RepositoryIntelligence) -> list[str]:
    lines = []
    for evidence in intelligence.technology_evidence[:100]:
        location = f"{evidence.file}:{evidence.line}" if evidence.line else evidence.file
        detail = f"; {evidence.detail}" if evidence.detail else ""
        lines.append(f"- {evidence.value} [{evidence.confidence}] — {location}{detail}")
    return lines or ["- none detected"]


def _architecture_evidence(intelligence: RepositoryIntelligence) -> list[str]:
    lines = ["ARCHITECTURE EVIDENCE COLLECTED PROGRAMMATICALLY", "", "Runtime and framework evidence:"]
    lines.extend(_technology_evidence(intelligence))
    lines.extend(["", "Detected languages:"])
    lines.extend(f"- {language}: {count} source files" for language, count in sorted(intelligence.languages.items())) or lines.append("- none detected")
    lines.extend(["", "Application topology:", *_topology(intelligence)])
    lines.extend(["", "Entry points:"])
    lines.extend(f"- {path}" for path in intelligence.entry_points[:80]) or lines.append("- none detected")
    lines.extend(["", "Routes and page files:"])
    lines.extend(f"- {path}" for path in (intelligence.api_routes + intelligence.page_files)[:160]) or lines.append("- none detected")
    lines.extend(["", "Configuration and CI/deployment evidence:"])
    lines.extend(f"- {path}" for path in (intelligence.config_files + intelligence.ci_files)[:120]) or lines.append("- none detected")
    lines.extend(["", "External integration candidates:"])
    integration = _signal_files(intelligence, {"integration"})
    lines.extend(f"- {path}" for path in integration) or lines.append("- none detected")
    lines.extend(["", "State-management candidates:"])
    state = _signal_files(intelligence, {"state"})
    lines.extend(f"- {path}" for path in state) or lines.append("- none detected")
    lines.extend(["", "Caching and revalidation candidates:"])
    cache = _signal_files(intelligence, {"cache"})
    lines.extend(f"- {path}" for path in cache) or lines.append("- none detected")
    lines.extend(["", "Environment-variable evidence:"])
    for evidence in intelligence.env_variable_evidence[:120]:
        location = f"{evidence.file}:{evidence.line}" if evidence.line else evidence.file
        lines.append(f"- {evidence.value} — {location}")
    if not intelligence.env_variable_evidence:
        lines.append("- none detected")
    lines.extend(["", "Resolved local dependency graph:"])
    lines.extend(_dependency_edges(intelligence)) or lines.append("- none detected")
    return lines


def _pattern_evidence(intelligence: RepositoryIntelligence) -> list[str]:
    groups = {
        "Provider/Context candidates": {"context"},
        "Adapter candidates": {"adapter", "integration"},
        "Repository candidates": {"repository"},
        "Factory candidates": {"factory"},
        "Observer/subscription candidates": {"observer"},
    }
    lines = ["PATTERN EVIDENCE COLLECTED PROGRAMMATICALLY"]
    for title, signals in groups.items():
        matches = _signal_files(intelligence, signals)
        lines.extend(["", title + ":"])
        lines.extend(f"- {path}" for path in matches) if matches else lines.append("- no conventional candidate detected")

    lines.extend(["", "Structural symbols in candidate files:"])
    candidates = set(sum((_signal_files(intelligence, signals) for signals in groups.values()), []))
    by_path = {item.path: item for item in intelligence.source_files}
    for path in sorted(candidates)[:100]:
        item = by_path[path]
        symbols = [f"{kind}: {', '.join(names[:20])}" for kind, names in item.symbols.items() if names]
        if symbols:
            lines.append(f"- {path} — " + "; ".join(symbols))
    lines.extend(["", "Local dependency relationships:", *_dependency_edges(intelligence)])
    return lines


def _requirements_evidence(intelligence: RepositoryIntelligence) -> list[str]:
    lines = ["REQUIREMENTS EVIDENCE COLLECTED PROGRAMMATICALLY", "", "Application entry points:"]
    lines.extend(f"- {path}" for path in intelligence.entry_points[:80]) or lines.append("- none detected")
    lines.extend(["", "API routes / operations:"])
    lines.extend(f"- {path}" for path in intelligence.api_routes[:160]) or lines.append("- none detected")
    lines.extend(["", "Pages / user-facing surfaces:"])
    lines.extend(f"- {path}" for path in intelligence.page_files[:160]) or lines.append("- none detected")
    lines.extend(["", "Potential operation-bearing symbols:"])
    by_path = {item.path: item for item in intelligence.source_files}
    operation_words = ("create", "update", "delete", "remove", "get", "list", "search", "login", "logout", "register", "upload", "export", "analyze", "generate")
    count = 0
    for item in intelligence.source_files:
        names = [name for names in item.symbols.values() for name in names if any(word in name.lower() for word in operation_words)]
        if names:
            lines.append(f"- {item.path}: {', '.join(names[:30])}")
            count += 1
            if count >= 120:
                break
    if count == 0:
        lines.append("- none detected")
    lines.extend(["", "Relevant dependency relationships:", *_dependency_edges(intelligence)])
    return lines


def _baseline(intelligence: RepositoryIntelligence) -> list[str]:
    return [
        "REPOSITORY BASELINE",
        f"Repository files considered: {intelligence.file_count}",
        f"Technologies: {', '.join(intelligence.technologies) or 'not detected'}",
        f"Environment variables: {', '.join(intelligence.env_variables) or 'none detected'}",
        f"Package scripts: {intelligence.package_scripts}",
        f"Tree-sitter parsing: {intelligence.parse_summary.get('parsed', 0)} parsed / {intelligence.parse_summary.get('failed', 0)} failed",
    ]


def _generic_evidence(intelligence: RepositoryIntelligence, phase: str) -> list[str]:
    lines = [f"PROGRAMMATIC EVIDENCE FOR {phase}", "", "Directory structure:", *_topology(intelligence), "", "Routes:"]
    lines.extend(f"- {path}" for path in intelligence.routes[:120]) or lines.append("- none detected")
    lines.extend(["", "Tests:"])
    lines.extend(f"- {path}" for path in intelligence.test_files[:120]) or lines.append("- none detected")
    lines.extend(["", "Dependency relationships:", *_dependency_edges(intelligence)])
    return lines


def build_phase_intelligence(intelligence: RepositoryIntelligence, phase: str) -> str:
    lines = [
        f"PHASE-SPECIFIC DETERMINISTIC INTELLIGENCE: {phase}",
        "The following evidence was collected programmatically before the LLM started. Treat verified facts as repository evidence, distinguish inference from fact, and do not repeat repository-wide discovery merely to rediscover these facts.",
        "",
        *_baseline(intelligence),
        "",
    ]
    if phase == "technology-architecture":
        lines.extend(_architecture_evidence(intelligence))
    elif phase == "design-pattern":
        lines.extend(_pattern_evidence(intelligence))
    elif phase == "software-requirements":
        lines.extend(_requirements_evidence(intelligence))
    else:
        lines.extend(_generic_evidence(intelligence, phase))
    if phase == "future-directions":
        markers = [f"- {item.path}: {', '.join(item.markers)}" for item in intelligence.source_files if item.markers]
        lines.extend(["", "Explicit maintenance and technical-debt markers:", *(markers[:100] or ["- none detected"])])
    return "\n".join(lines)


def collect_phase_intelligence(repository, phase: str, intelligence: RepositoryIntelligence | None = None) -> tuple[RepositoryIntelligence, str]:
    intelligence = intelligence or collect_repository_intelligence(repository)
    return intelligence, build_phase_intelligence(intelligence, phase)
