"""Deterministic repository intelligence extraction."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

TEXT_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".mdx", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".css", ".scss", ".mjs", ".cjs", ".html", ".sql", ".graphql", ".gql", ".env", ".txt", ".xml", ".properties"}
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build"}
MAX_FILES = 3000
MAX_TEXT_BYTES_PER_FILE = 500_000


def _iter_files(root: Path) -> Iterable[Path]:
    count = 0
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.parts) or not path.is_file():
            continue
        yield path
        count += 1
        if count >= MAX_FILES:
            return


def _read_text(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES_PER_FILE:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    
def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()

def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _imports(text: str) -> list[str]:
    patterns = [r"(?:from|import)\s+['\"]([^'\"]+)['\"]", r"from\s+['\"]([^'\"]+)['\"]", r"require\(\s*['\"]([^'\"]+)['\"]\s*\)"]
    out: list[str] = []
    for pattern in patterns:
        out.extend(re.findall(pattern, text))
    return _unique(out)[:100]


def _exports(text: str) -> list[str]:
    out = re.findall(r"export\s+(?:async\s+)?(?:function|class|const|let|var|type|interface)\s+([A-Za-z_$][\w$]*)", text)
    return _unique(out)[:100]


def _symbols(text: str) -> dict[str, list[str]]:
    return {
        "functions": _unique(re.findall(r"\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", text))[:100],
        "classes": _unique(re.findall(r"\bclass\s+([A-Za-z_$][\w$]*)", text))[:100],
        "interfaces": _unique(re.findall(r"\binterface\s+([A-Za-z_$][\w$]*)", text))[:100],
        "types": _unique(re.findall(r"\btype\s+([A-Za-z_$][\w$]*)\s*=", text))[:100],
    }


@dataclass
class FileIntelligence:
    path: str
    extension: str
    size: int
    line_count: int
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    symbols: dict[str, list[str]] = field(default_factory=dict)
    markers: list[str] = field(default_factory=list)


@dataclass
class RepositoryIntelligence:
    root: str
    file_count: int
    files: list[str]
    directories: list[str]
    technologies: list[str]
    package_scripts: dict[str, str]
    dependencies: dict[str, str]
    dev_dependencies: dict[str, str]
    env_variables: list[str]
    routes: list[str]
    page_files: list[str]
    api_routes: list[str]
    test_files: list[str]
    config_files: list[str]
    ci_files: list[str]
    documentation_files: list[str]
    integration_files: list[str]
    source_files: list[FileIntelligence]

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


def _package(root: Path) -> dict:
    path = root / "package.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(_read_text(path))
    except (TypeError, json.JSONDecodeError):
        return {}


def _detect_technologies(root: Path, package: dict, files: list[str]) -> list[str]:
    deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    lower = "\n".join(files).lower()
    mapping = {
        "next": "Next.js", "react": "React", "typescript": "TypeScript", "tailwindcss": "Tailwind CSS",
        "fastapi": "FastAPI", "pydantic": "Pydantic", "django": "Django", "flask": "Flask",
        "pytest": "Pytest", "playwright": "Playwright", "cypress": "Cypress", "jest": "Jest",
        "vitest": "Vitest", "graphql": "GraphQL", "openai": "OpenAI", "docker": "Docker",
    }
    result = [label for key, label in mapping.items() if key in deps or key in lower]
    if (root / "requirements.txt").is_file() or (root / "pyproject.toml").is_file():
        result.append("Python")
    if (root / "package.json").is_file():
        result.append("Node.js")
    return _unique(result)


def collect_repository_intelligence(repository: Path) -> RepositoryIntelligence:
    root = repository.resolve()
    if not root.is_dir():
        raise ValueError(f"Repository path does not exist: {repository}")
    paths = list(_iter_files(root))
    files = [_relative(path, root) for path in paths]
    package = _package(root)
    dirs = _unique(parent.as_posix() for path in paths for parent in path.relative_to(root).parents if parent.as_posix() != ".")
    source: list[FileIntelligence] = []
    routes: list[str] = []
    page_files: list[str] = []
    api_routes: list[str] = []
    test_files: list[str] = []
    config_files: list[str] = []
    ci_files: list[str] = []
    docs: list[str] = []
    integration_files: list[str] = []
    env_vars: list[str] = []

    config_names = {"package.json", "requirements.txt", "pyproject.toml", "tsconfig.json", "next.config.ts", "next.config.js", "next.config.mjs", "vite.config.ts", "postcss.config.mjs", "tailwind.config.js", "tailwind.config.ts", "dockerfile", "docker-compose.yml"}
    integration_tokens = ("shopify", "stripe", "postgres", "mysql", "redis", "kafka", "aws", "gcp", "azure", "openai", "graphql")
    for path in paths:
        rel = _relative(path, root)
        lower = rel.lower()
        ext = path.suffix.lower()
        name = path.name.lower()
        if name in config_names:
            config_files.append(rel)
        if lower.startswith(".github/"):
            ci_files.append(rel)
        if ext in {".md", ".mdx"} or name.startswith("readme"):
            docs.append(rel)
        if re.search(r"(^|/)(tests?|spec|__tests__)(/|$)|\.(test|spec)\.[^.]+$", lower):
            test_files.append(rel)
        if re.search(r"(^|/)(route|api)(/|$)|route\.[jt]sx?$", lower):
            routes.append(rel)
        if lower.endswith(("/route.ts", "/route.js", "/route.py")) or "/api/" in lower:
            api_routes.append(rel)
        if re.search(r"(^|/)(page|pages)(/|$)|/page\.[jt]sx?$", lower):
            page_files.append(rel)
        text = _read_text(path) if ext in TEXT_EXTENSIONS or name in {"dockerfile", "makefile"} else ""
        if not text:
            continue
        if name.startswith(".env"):
            env_vars.extend(m.group(1) for m in (re.match(r"\s*([A-Z][A-Z0-9_]+)\s*=", line) for line in text.splitlines()) if m)
        imports = _imports(text)
        exports = _exports(text)
        symbols = _symbols(text)
        markers = _unique(re.findall(r"\b(?:TODO|FIXME|HACK|XXX|DEPRECATED)\b", text, flags=re.I))
        source.append(FileIntelligence(rel, ext, path.stat().st_size, text.count("\n") + 1, imports, exports, symbols, markers))
        if any(token in lower for token in integration_tokens):
            integration_files.append(rel)

    return RepositoryIntelligence(
        root=str(root), file_count=len(files), files=files, directories=dirs,
        technologies=_detect_technologies(root, package, files),
        package_scripts={str(k): str(v) for k, v in package.get("scripts", {}).items()},
        dependencies={str(k): str(v) for k, v in package.get("dependencies", {}).items()},
        dev_dependencies={str(k): str(v) for k, v in package.get("devDependencies", {}).items()},
        env_variables=_unique(env_vars), routes=_unique(routes), page_files=_unique(page_files),
        api_routes=_unique(api_routes), test_files=_unique(test_files), config_files=_unique(config_files),
        ci_files=_unique(ci_files), documentation_files=_unique(docs), integration_files=_unique(integration_files), source_files=source,
    )
