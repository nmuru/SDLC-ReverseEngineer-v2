"""Phase-specific projections of deterministic repository intelligence."""
from __future__ import annotations

from pathlib import Path

from .repository_intelligence import RepositoryIntelligence, collect_repository_intelligence

PHASE_FILE_TOKENS: dict[str, tuple[str, ...]] = {
    "business-purpose": ("README", "LICENSE", "docs", "app/", "src/"),
    "features": ("app/", "components/", "pages/", "src/", "README", "routes"),
    "business-requirements": ("app/", "components/", "pages/", "src/", "README", "api/"),
    "software-requirements": ("app/", "components/", "lib/", "src/", "api/", "queries/", "mutations/"),
    "technology-architecture": ("next.config", "package.json", "tsconfig", "app/", "components/", "lib/", "services/", "api/", "Docker", "docker"),
    "design-pattern": ("components/", "lib/", "services/", "domain/", "app/", "actions", "context", "provider", "adapter", "factory", "repository"),
    "high-level-design": ("app/", "components/", "lib/", "services/", "api/", "routes/", "domain/", "repositories/", "package.json"),
    "low-level-design": ("app/", "components/", "lib/", "services/", "domain/", "types", "queries/", "mutations/", "actions"),
    "implementation-detail": ("app/", "components/", "lib/", "services/", "domain/", "queries/", "mutations/", "actions", "config"),
    "testing-harness": ("test", "tests", "spec", "__tests__", ".github/", "package.json", "vitest", "jest", "playwright", "cypress", "pytest"),
    "future-directions": ("README", ".github/", "package.json", "requirements", "TODO", "FIXME", "DEPRECATED", "next.config", "tsconfig"),
}


def _relevant_files(intelligence: RepositoryIntelligence, phase: str, limit: int = 180) -> list[str]:
    tokens = PHASE_FILE_TOKENS.get(phase, ())
    if not tokens:
        return intelligence.files[:limit]
    selected = [
        path for path in intelligence.files
        if any(token.lower() in path.lower() for token in tokens)
    ]
    return selected[:limit]


def _file_rows(intelligence: RepositoryIntelligence, files: list[str], limit: int = 120) -> list[str]:
    by_path = {item.path: item for item in intelligence.source_files}
    rows: list[str] = []
    for path in files[:limit]:
        item = by_path.get(path)
        if not item:
            rows.append(f"- {path}")
            continue
        symbols = "; ".join(
            f"{kind}: {', '.join(values[:30])}" for kind, values in item.symbols.items() if values
        )
        rows.append(f"- {path} | lines={item.line_count} | imports={', '.join(item.imports[:25])} | exports={', '.join(item.exports[:25])} | {symbols}")
    return rows


def build_phase_intelligence(intelligence: RepositoryIntelligence, phase: str) -> str:
    relevant = _relevant_files(intelligence, phase)
    rows = _file_rows(intelligence, relevant)
    lines = [
        f"PHASE-SPECIFIC DETERMINISTIC INTELLIGENCE: {phase}",
        "This package is generated locally before the LLM starts. Treat it as the primary evidence index. Use repository tools only to resolve a specific ambiguity or inspect a source passage needed for precision.",
        "",
        "REPOSITORY BASELINE",
        f"Repository files: {intelligence.file_count}",
        f"Technologies: {', '.join(intelligence.technologies) or 'not detected'}",
        f"Environment variables: {', '.join(intelligence.env_variables) or 'none detected'}",
        f"Routes: {', '.join(intelligence.routes[:120]) or 'none detected'}",
        f"API routes: {', '.join(intelligence.api_routes[:120]) or 'none detected'}",
        f"Pages: {', '.join(intelligence.page_files[:120]) or 'none detected'}",
        f"Tests: {', '.join(intelligence.test_files[:120]) or 'none detected'}",
        f"CI: {', '.join(intelligence.ci_files[:80]) or 'none detected'}",
        f"Config: {', '.join(intelligence.config_files[:80]) or 'none detected'}",
        f"Integrations: {', '.join(intelligence.integration_files[:120]) or 'none detected'}",
        f"Package scripts: {intelligence.package_scripts}",
        "",
        "PHASE-RELEVANT SOURCE INDEX",
        *rows,
    ]

    if phase == "technology-architecture":
        lines.extend([
            "",
            "ARCHITECTURE FOCUS",
            "Identify runtime/platform, application layers, module boundaries, external systems, data flow, state flow, communication mechanisms, caching/revalidation, deployment configuration, and key dependency relationships.",
        ])
    elif phase == "design-pattern":
        lines.extend([
            "",
            "PATTERN FOCUS",
            "Look for concrete recurring structures: context/provider, server/client separation, server actions, adapters, repositories, factories, strategies, observers, composition, dependency inversion, and framework-specific patterns. Name a pattern only when implementation evidence supports it.",
        ])
    elif phase == "high-level-design":
        lines.extend([
            "",
            "HLD FOCUS",
            "Group source files into coarse-grained components and explain responsibilities and interactions. Prefer component boundaries over individual functions.",
        ])
    elif phase == "low-level-design":
        lines.extend([
            "",
            "LLD FOCUS",
            "Use the indexed functions, classes, interfaces, types, imports, exports, queries, mutations, and actions to explain detailed structure and call/data relationships.",
        ])
    elif phase == "testing-harness":
        lines.extend([
            "",
            "TESTING FOCUS",
            "Determine actual test frameworks, test files, scripts, CI workflows, testable seams, mocks/fixtures, and gaps. Explicitly distinguish formatting/linting checks from real executable tests.",
        ])
    elif phase == "future-directions":
        markers = []
        for item in intelligence.source_files:
            if item.markers:
                markers.append(f"{item.path}: {', '.join(item.markers)}")
        lines.extend([
            "",
            "FUTURE-DIRECTIONS FOCUS",
            "Use explicit repository intent first. Where explicit future intent is absent, derive conservative opportunities from architecture, dependency/configuration state, test maturity, extension points, and evidence of technical debt. Do not manufacture a roadmap.",
            "Markers: " + (" | ".join(markers[:80]) or "none detected"),
        ])
    return "\n".join(lines)


def collect_phase_intelligence(repository: Path, phase: str) -> tuple[RepositoryIntelligence, str]:
    intelligence = collect_repository_intelligence(repository)
    return intelligence, build_phase_intelligence(intelligence, phase)
