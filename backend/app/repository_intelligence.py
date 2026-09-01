"""Deterministic repository pre-analysis for reverse-engineering phases.

This module performs common discovery work once per cloned repository.  The
result is compact, structured evidence that can be supplied to every selected
phase before the LLM decides whether additional investigation is necessary.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TEXT_SUFFIXES = {
    ".java", ".kt", ".kts", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".json", ".yml", ".yaml", ".xml", ".properties", ".gradle", ".md",
    ".txt", ".html", ".css", ".scss", ".sql", ".sh", ".toml", ".conf",
}
SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", ".next", "coverage", "vendor", ".venv", "__pycache__"}
IMPORTANT_NAMES = {
    "README.md", "README", "package.json", "pom.xml", "build.gradle",
    "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml", "Makefile", ".env.example",
}


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in IMPORTANT_NAMES


def _safe_read(path: Path, max_chars: int = 20000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return ""


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _detect_technologies(root: Path, files: list[Path]) -> list[str]:
    names = {path.name for path in files}
    technologies: list[str] = []
    package = _safe_read(root / "package.json") if "package.json" in names else ""
    pom = _safe_read(root / "pom.xml") if "pom.xml" in names else ""
    gradle = "\n".join(_safe_read(path) for path in files if path.name in {"build.gradle", "build.gradle.kts"})
    all_paths = "\n".join(_relative(root, path) for path in files)

    if "next.config.js" in names or "next.config.ts" in names or "\"next\"" in package:
        technologies.append("Next.js")
    if "\"react\"" in package or any(path.suffix.lower() in {".jsx", ".tsx"} for path in files):
        technologies.append("React")
    if "spring-boot" in pom.lower() or "spring-boot" in gradle.lower() or "@springbootapplication" in all_paths.lower():
        technologies.append("Spring Boot")
    if "spring" in pom.lower() and "Spring Boot" not in technologies:
        technologies.append("Spring")
    if "quarkus" in pom.lower() or "quarkus" in gradle.lower():
        technologies.append("Quarkus")
    if "django" in package.lower() or any("django" in _safe_read(path, 5000).lower() for path in files if path.name == "requirements.txt"):
        technologies.append("Django")
    if "fastapi" in "\n".join(_safe_read(path, 5000) for path in files if path.name in {"requirements.txt", "pyproject.toml"}).lower():
        technologies.append("FastAPI")
    if "dockerfile" in {name.lower() for name in names}:
        technologies.append("Docker")
    if ".github/workflows/" in all_paths:
        technologies.append("GitHub Actions")
    return technologies


def _classify_paths(root: Path, files: list[Path]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for path in files:
        rel = _relative(root, path)
        lower = rel.lower()
        if path.name in IMPORTANT_NAMES:
            groups["metadata_and_build"].append(rel)
        if "test" in lower or "spec" in lower:
            groups["tests"].append(rel)
        if ".github/workflows/" in lower or "gitlab-ci" in lower or "jenkins" in lower:
            groups["ci_cd"].append(rel)
        if any(token in lower for token in ("docker", "kubernetes", "k8s", "helm", "terraform", "ansible")):
            groups["deployment_and_infrastructure"].append(rel)
        if any(token in lower for token in ("config", "application.yml", "application.yaml", "application.properties", ".env")):
            groups["configuration"].append(rel)
        if any(token in lower for token in ("controller", "route", "/api/", "api/", "router")):
            groups["api_and_routes"].append(rel)
        if any(token in lower for token in ("service", "usecase", "use-case")):
            groups["services"].append(rel)
        if any(token in lower for token in ("repository", "dao", "entity", "model", "domain")):
            groups["domain_and_data"].append(rel)
        if any(token in lower for token in ("component", "components/", "page", "view", "layout", "template")):
            groups["presentation"].append(rel)
    return {key: values[:200] for key, values in sorted(groups.items())}


def _extract_route_candidates(root: Path, files: list[Path]) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for path in files:
        rel = _relative(root, path)
        lower = rel.lower()
        if lower.endswith(("route.ts", "route.js", "route.py")) or "/api/" in lower or "controller" in lower:
            routes.append({"file": rel, "reason": "route/API naming convention"})
    return routes[:100]


def _extract_external_integration_candidates(root: Path, files: list[Path]) -> list[dict[str, str]]:
    patterns = re.compile(r"\b(shopify|stripe|aws|azure|gcp|google|github|kafka|rabbitmq|redis|postgres|mysql|mongodb|elasticsearch)\b", re.I)
    found: list[dict[str, str]] = []
    for path in files:
        if not _is_text_file(path):
            continue
        text = _safe_read(path, 12000)
        matches = sorted(set(match.group(1).lower() for match in patterns.finditer(text)))
        if matches:
            found.append({"file": _relative(root, path), "matches": ", ".join(matches)})
    return found[:100]


def build_repository_intelligence(repository: Path, repo_url: str) -> dict[str, Any]:
    """Perform deterministic common discovery once and return JSON-safe evidence."""
    root = repository.resolve()
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            files.append(path)
    files.sort(key=lambda path: _relative(root, path))

    suffix_counts = Counter(path.suffix.lower() or "[no extension]" for path in files)
    important = [path for path in files if path.name in IMPORTANT_NAMES]
    top_level = sorted({path.relative_to(root).parts[0] for path in files if path.relative_to(root).parts})

    return {
        "repository_url": repo_url,
        "repository_root": str(root),
        "summary": {
            "file_count": len(files),
            "top_level_entries": top_level[:100],
            "file_types": suffix_counts.most_common(30),
            "technologies_detected": _detect_technologies(root, files),
        },
        "important_files": [
            {"path": _relative(root, path), "content": _safe_read(path, 12000)}
            for path in important[:30]
        ],
        "file_tree": [_relative(root, path) for path in files[:1000]],
        "semantic_groups": _classify_paths(root, files),
        "route_candidates": _extract_route_candidates(root, files),
        "integration_candidates": _extract_external_integration_candidates(root, files),
    }


def intelligence_for_prompt(intelligence: dict[str, Any], max_chars: int = 45000) -> str:
    """Serialize pre-analysis with an explicit boundary for the LLM."""
    text = json.dumps(intelligence, ensure_ascii=False, indent=2)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[TRUNCATED: use repository evidence tools for details not included above]"
    return "DETERMINISTIC REPOSITORY INTELLIGENCE (evidence collected before this phase):\n" + text
