"""Deterministic repository intelligence extraction.

The repository scan is intentionally LLM-free. It extracts cheap, reproducible facts
that can be projected into individual SDLC phases before an agent starts reasoning.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from tree_sitter_language_pack import get_parser
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    get_parser = None  # type: ignore[assignment]

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".mdx", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".css", ".scss", ".mjs", ".cjs", ".html", ".sql",
    ".graphql", ".gql", ".env", ".txt", ".xml", ".properties",
}
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build"}
MAX_FILES = 3000
MAX_TEXT_BYTES_PER_FILE = 500_000
MAX_ITEMS_PER_FILE = 100

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
}


@dataclass
class Evidence:
    """A machine-derived fact with enough provenance to audit it."""

    kind: str
    value: str
    file: str
    line: int | None = None
    detail: str | None = None
    confidence: str = "verified"


@dataclass
class DependencyEdge:
    source: str
    target: str
    kind: str = "local-import"
    imported_as: str | None = None
    confidence: str = "verified"


@dataclass
class SymbolIntelligence:
    name: str
    kind: str
    line: int
    exported: bool = False


@dataclass
class FileIntelligence:
    path: str
    extension: str
    size: int
    line_count: int
    language: str | None = None
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    symbols: dict[str, list[str]] = field(default_factory=dict)
    symbol_details: list[SymbolIntelligence] = field(default_factory=list)
    resolved_local_imports: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)
    parse_status: str = "not-attempted"


@dataclass
class RepositoryIntelligence:
    """Versioned, serializable repository knowledge used by phase projections."""

    schema_version: str
    root: str
    file_count: int
    files: list[str]
    directories: list[str]
    languages: dict[str, int]
    technologies: list[str]
    technology_evidence: list[Evidence]
    package_scripts: dict[str, str]
    dependencies: dict[str, str]
    dev_dependencies: dict[str, str]
    env_variables: list[str]
    env_variable_evidence: list[Evidence]
    routes: list[str]
    page_files: list[str]
    api_routes: list[str]
    entry_points: list[str]
    test_files: list[str]
    config_files: list[str]
    ci_files: list[str]
    documentation_files: list[str]
    integration_files: list[str]
    dependency_edges: list[DependencyEdge]
    source_files: list[FileIntelligence]
    parse_summary: dict[str, int]

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


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
    patterns = [
        r"(?:from|import)\s+['\"]([^'\"]+)['\"]",
        r"from\s+['\"]([^'\"]+)['\"]",
        r"require\(\s*['\"]([^'\"]+)['\"]\s*\)",
    ]
    out: list[str] = []
    for pattern in patterns:
        out.extend(re.findall(pattern, text))
    return _unique(out)[:MAX_ITEMS_PER_FILE]


def _exports(text: str) -> list[str]:
    out = re.findall(
        r"export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var|type|interface)\s+([A-Za-z_$][\w$]*)",
        text,
    )
    return _unique(out)[:MAX_ITEMS_PER_FILE]


def _symbols(text: str) -> dict[str, list[str]]:
    return {
        "functions": _unique(re.findall(r"\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", text))[:MAX_ITEMS_PER_FILE],
        "classes": _unique(re.findall(r"\bclass\s+([A-Za-z_$][\w$]*)", text))[:MAX_ITEMS_PER_FILE],
        "interfaces": _unique(re.findall(r"\binterface\s+([A-Za-z_$][\w$]*)", text))[:MAX_ITEMS_PER_FILE],
        "types": _unique(re.findall(r"\btype\s+([A-Za-z_$][\w$]*)\s*=", text))[:MAX_ITEMS_PER_FILE],
    }


def _language_for(path: Path) -> str | None:
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower())


def _node_line(node) -> int:
    return int(node.start_point[0]) + 1


def _walk_tree(root_node):
    stack = [root_node]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node.children))


def _ast_symbols(text: str, language: str) -> tuple[dict[str, list[str]], list[SymbolIntelligence], str]:
    """Extract structural symbols with Tree-sitter, falling back gracefully on parse issues."""
    if get_parser is None:
        return {}, [], "parser-unavailable"
    try:
        parser = get_parser(language)
        tree = parser.parse(text.encode("utf-8"))
    except Exception:
        return {}, [], "parse-error"

    type_map = {
        "function_declaration": "functions",
        "function_definition": "functions",
        "method_definition": "methods",
        "class_declaration": "classes",
        "class_definition": "classes",
        "interface_declaration": "interfaces",
        "type_alias_declaration": "types",
        "enum_declaration": "enums",
    }
    name_node_types = {"identifier", "type_identifier", "property_identifier"}
    grouped: dict[str, list[str]] = {}
    details: list[SymbolIntelligence] = []
    for node in _walk_tree(tree.root_node):
        kind = type_map.get(node.type)
        if not kind:
            continue
        name = None
        for child in node.children:
            if child.type in name_node_types:
                name = child.text.decode("utf-8", errors="replace")
                break
        if not name:
            continue
        grouped.setdefault(kind, []).append(name)
        details.append(SymbolIntelligence(name=name, kind=kind, line=_node_line(node)))

    for values in grouped.values():
        del values[MAX_ITEMS_PER_FILE:]
    details = details[:MAX_ITEMS_PER_FILE]
    return grouped, details, "parsed"


def _resolve_js_import(importer: Path, specifier: str, root: Path) -> str | None:
    if not specifier.startswith("."):
        return None
    base = (importer.parent / specifier).resolve()
    candidates = [base]
    for extension in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        candidates.append(Path(str(base) + extension))
    candidates.extend(base / f"index{extension}" for extension in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"))
    for candidate in candidates:
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate.relative_to(root).as_posix()
    return None


def _resolve_python_import(importer: Path, specifier: str, root: Path) -> str | None:
    if specifier.startswith("."):
        dots = len(specifier) - len(specifier.lstrip("."))
        module = specifier[dots:].replace(".", "/")
        base = importer.parent
        for _ in range(max(0, dots - 1)):
            base = base.parent
        candidates = [base / f"{module}.py", base / module / "__init__.py"]
    else:
        module = specifier.replace(".", "/")
        candidates = [root / f"{module}.py", root / module / "__init__.py"]
    for candidate in candidates:
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate.relative_to(root).as_posix()
    return None


def _resolve_local_import(importer: Path, specifier: str, root: Path, language: str | None) -> str | None:
    if language in {"javascript", "typescript", "tsx"}:
        return _resolve_js_import(importer, specifier, root)
    if language == "python":
        return _resolve_python_import(importer, specifier, root)
    return None


def _package(root: Path) -> dict:
    path = root / "package.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(_read_text(path))
    except (TypeError, json.JSONDecodeError):
        return {}


def _technology_evidence(root: Path, package: dict, files: list[str]) -> tuple[list[str], list[Evidence]]:
    deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    lower = "\n".join(files).lower()
    mapping = {
        "next": "Next.js", "react": "React", "typescript": "TypeScript", "tailwindcss": "Tailwind CSS",
        "fastapi": "FastAPI", "pydantic": "Pydantic", "django": "Django", "flask": "Flask",
        "pytest": "Pytest", "playwright": "Playwright", "cypress": "Cypress", "jest": "Jest",
        "vitest": "Vitest", "graphql": "GraphQL", "openai": "OpenAI", "docker": "Docker",
    }
    result: list[str] = []
    evidence: list[Evidence] = []
    for key, label in mapping.items():
        if key in deps:
            result.append(label)
            evidence.append(Evidence("technology", label, "package.json", detail=f"dependency {key}={deps[key]}"))
        elif key in lower:
            result.append(label)
            matching_file = next((path for path in files if key in path.lower()), "repository path")
            evidence.append(Evidence("technology", label, matching_file, detail="technology token found in repository path", confidence="inferred"))
    if (root / "requirements.txt").is_file() or (root / "pyproject.toml").is_file():
        result.append("Python")
        evidence.append(Evidence("technology", "Python", "requirements.txt" if (root / "requirements.txt").is_file() else "pyproject.toml", detail="Python project metadata present"))
    if (root / "package.json").is_file():
        result.append("Node.js")
        evidence.append(Evidence("technology", "Node.js", "package.json", detail="Node package metadata present"))
    return _unique(result), evidence


def collect_repository_intelligence(repository: Path) -> RepositoryIntelligence:
    root = repository.resolve()
    if not root.is_dir():
        raise ValueError(f"Repository path does not exist: {repository}")

    paths = list(_iter_files(root))
    files = [_relative(path, root) for path in paths]
    package = _package(root)
    dirs = _unique(parent.as_posix() for path in paths for parent in path.relative_to(root).parents if parent.as_posix() != ".")

    source: list[FileIntelligence] = []
    dependency_edges: list[DependencyEdge] = []
    languages: dict[str, int] = {}
    routes: list[str] = []
    page_files: list[str] = []
    api_routes: list[str] = []
    entry_points: list[str] = []
    test_files: list[str] = []
    config_files: list[str] = []
    ci_files: list[str] = []
    docs: list[str] = []
    integration_files: list[str] = []
    env_vars: list[str] = []
    env_evidence: list[Evidence] = []
    parse_summary = {"attempted": 0, "parsed": 0, "failed": 0}

    config_names = {
        "package.json", "requirements.txt", "pyproject.toml", "tsconfig.json", "next.config.ts",
        "next.config.js", "next.config.mjs", "vite.config.ts", "postcss.config.mjs", "tailwind.config.js",
        "tailwind.config.ts", "dockerfile", "docker-compose.yml",
    }
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
        if lower.endswith(("/route.ts", "/route.tsx", "/route.js", "/route.jsx", "/route.py")) or "/api/" in lower:
            api_routes.append(rel)
        if re.search(r"(^|/)(page|pages)(/|$)|/page\.[jt]sx?$", lower):
            page_files.append(rel)
        if name in {"main.py", "app.py", "server.py", "manage.py", "index.ts", "index.tsx", "index.js", "index.jsx"}:
            entry_points.append(rel)

        language = _language_for(path)
        if language:
            languages[language] = languages.get(language, 0) + 1
        text = _read_text(path) if ext in TEXT_EXTENSIONS or name in {"dockerfile", "makefile"} else ""
        if not text:
            continue

        if name.startswith(".env"):
            for line_no, line in enumerate(text.splitlines(), 1):
                match = re.match(r"\s*([A-Z][A-Z0-9_]+)\s*=", line)
                if match:
                    variable = match.group(1)
                    env_vars.append(variable)
                    env_evidence.append(Evidence("environment-variable", variable, rel, line=line_no, detail="assignment found"))

        imports = _imports(text)
        exports = _exports(text)
        regex_symbols = _symbols(text)
        ast_symbols: dict[str, list[str]] = {}
        symbol_details: list[SymbolIntelligence] = []
        parse_status = "not-attempted"
        if language:
            parse_summary["attempted"] += 1
            ast_symbols, symbol_details, parse_status = _ast_symbols(text, language)
            if parse_status == "parsed":
                parse_summary["parsed"] += 1
            else:
                parse_summary["failed"] += 1

        merged_symbols: dict[str, list[str]] = {}
        for kind in set(regex_symbols) | set(ast_symbols):
            merged_symbols[kind] = _unique([*ast_symbols.get(kind, []), *regex_symbols.get(kind, [])])[:MAX_ITEMS_PER_FILE]

        exported_set = set(exports)
        for detail in symbol_details:
            detail.exported = detail.name in exported_set

        resolved_imports: list[str] = []
        for imported in imports:
            target = _resolve_local_import(path, imported, root, language)
            if target:
                resolved_imports.append(target)
                dependency_edges.append(DependencyEdge(rel, target, imported_as=imported))

        markers = _unique(re.findall(r"\b(?:TODO|FIXME|HACK|XXX|DEPRECATED)\b", text, flags=re.I))
        source.append(
            FileIntelligence(
                rel, ext, path.stat().st_size, text.count("\n") + 1, language, imports, exports,
                merged_symbols, symbol_details[:MAX_ITEMS_PER_FILE], _unique(resolved_imports), markers, parse_status,
            )
        )
        if any(token in lower for token in integration_tokens):
            integration_files.append(rel)

    technologies, technology_evidence = _technology_evidence(root, package, files)
    return RepositoryIntelligence(
        schema_version="1.1",
        root=str(root),
        file_count=len(files),
        files=files,
        directories=dirs,
        languages=languages,
        technologies=technologies,
        technology_evidence=technology_evidence,
        package_scripts={str(k): str(v) for k, v in package.get("scripts", {}).items()},
        dependencies={str(k): str(v) for k, v in package.get("dependencies", {}).items()},
        dev_dependencies={str(k): str(v) for k, v in package.get("devDependencies", {}).items()},
        env_variables=_unique(env_vars),
        env_variable_evidence=env_evidence,
        routes=_unique(routes),
        page_files=_unique(page_files),
        api_routes=_unique(api_routes),
        entry_points=_unique(entry_points),
        test_files=_unique(test_files),
        config_files=_unique(config_files),
        ci_files=_unique(ci_files),
        documentation_files=_unique(docs),
        integration_files=_unique(integration_files),
        dependency_edges=dependency_edges[:MAX_FILES * 10],
        source_files=source,
        parse_summary=parse_summary,
    )
