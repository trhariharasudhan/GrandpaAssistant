from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = PROJECT_ROOT / "backend" / "app"
DOCS_DIR = PROJECT_ROOT / "docs"
INVENTORY_DIR = DOCS_DIR / "inventory"

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head", "websocket", "api_route"}
MARKER_PATTERN = re.compile(r"\b(TODO|FIXME|deprecated|DEPRECATED)\b")

FOCUS_FILES = {
    "web_api": BACKEND_APP / "api" / "web_api.py",
    "chat_api": BACKEND_APP / "api" / "chat_api.py",
    "command_router": BACKEND_APP / "core" / "command_router.py",
    "unified_command_router": BACKEND_APP / "core" / "unified_command_router.py",
    "shared_llm_client": BACKEND_APP / "shared" / "llm_client.py",
    "shared_claude_client": BACKEND_APP / "shared" / "claude_client.py",
    "shared_offline_multi_model": BACKEND_APP / "shared" / "offline_multi_model.py",
    "assistant_database": BACKEND_APP / "shared" / "brain" / "database.py",
    "assistant_memory_engine": BACKEND_APP / "shared" / "brain" / "memory_engine.py",
    "semantic_memory": BACKEND_APP / "shared" / "brain" / "semantic_memory.py",
    "terminal_chat_memory": BACKEND_APP / "core" / "chatbot" / "memory.py",
}

PROVIDER_DIR = BACKEND_APP / "core" / "chatbot" / "providers"

DUPLICATE_ROUTE_DECISIONS = [
    {
        "route": "POST /api/automation/n8n/test",
        "active_owner": "backend/app/api/web_api.py::api_n8n_test",
        "secondary": "backend/app/api/chat_api.py::n8n_test",
        "decision": "KEEP_IN_WEB_API",
        "future_action": "Keep chat_api copy until alternate chat API ownership is decided.",
    },
    {
        "route": "POST /chat",
        "active_owner": "backend/app/api/web_api.py::chat_reply",
        "secondary": "backend/app/api/chat_api.py::chat",
        "decision": "KEEP_IN_WEB_API_NOW_MOVE_TO_CHAT_API_LATER",
        "future_action": "Move or consolidate only after the chat API contract and desktop API compatibility are explicit.",
    },
    {
        "route": "GET /chat/history",
        "active_owner": "backend/app/api/web_api.py::chat_history",
        "secondary": "backend/app/api/chat_api.py::get_chat_history",
        "decision": "KEEP_IN_WEB_API_NOW_MOVE_TO_CHAT_API_LATER",
        "future_action": "Preserve web_api behavior; later compare response schemas before consolidation.",
    },
    {
        "route": "POST /chat/reset",
        "active_owner": "backend/app/api/web_api.py::chat_reset",
        "secondary": "backend/app/api/chat_api.py::reset_chat",
        "decision": "KEEP_IN_WEB_API_NOW_MOVE_TO_CHAT_API_LATER",
        "future_action": "Preserve web_api behavior; later compare session reset semantics before consolidation.",
    },
    {
        "route": "POST /chat/stream",
        "active_owner": "backend/app/api/web_api.py::chat_stream",
        "secondary": "backend/app/api/chat_api.py::chat_stream",
        "decision": "KEEP_IN_WEB_API_NOW_MOVE_TO_CHAT_API_LATER",
        "future_action": "Preserve web_api streaming behavior; later align stream event format if chat_api becomes owner.",
    },
]


@dataclass(frozen=True)
class PythonFileInfo:
    path: Path
    rel_path: str
    module: str
    line_count: int
    marker_lines: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class ImportInfo:
    file: str
    module: str
    imported: str
    kind: str
    line: int
    legacy_risk: bool
    legacy_category: str


@dataclass(frozen=True)
class RouteInfo:
    file: str
    module: str
    method: str
    path: str
    function: str
    line: int
    owner_recommendation: str


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _module_name(path: Path) -> str:
    rel = path.relative_to(BACKEND_APP).with_suffix("")
    return ".".join(rel.parts)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _constant_text(node: ast.AST | None) -> str:
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Str):
        return str(node.s)
    return ""


def _literal_methods(node: ast.AST | None) -> list[str]:
    if node is None:
        return []
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [value.upper() for item in node.elts if (value := _constant_text(item))]
    value = _constant_text(node)
    return [value.upper()] if value else []


def _decorator_route(decorator: ast.AST) -> tuple[list[str], str] | None:
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    if not isinstance(func, ast.Attribute):
        return None
    attr = func.attr.lower()
    if attr not in HTTP_METHODS:
        return None

    path = _constant_text(decorator.args[0]) if decorator.args else ""
    if not path:
        return None

    if attr == "api_route":
        methods: list[str] = []
        for keyword in decorator.keywords:
            if keyword.arg == "methods":
                methods = _literal_methods(keyword.value)
                break
        return (methods or ["API_ROUTE"], path)

    return ([attr.upper()], path)


def _legacy_import_category(imported: str, file_path: str) -> str:
    normalized = imported.strip(".")
    if file_path.startswith("backend/app/features/modules/"):
        return "KEEP_COMPAT_NOW"
    if normalized == "modules" or normalized.startswith("modules."):
        return "NEEDS_RUNTIME_REVIEW"
    if normalized == "features.modules" or normalized.startswith("features.modules.") or ".features.modules" in normalized:
        return "NEEDS_RUNTIME_REVIEW"
    return ""


def _is_legacy_import(imported: str, file_path: str) -> bool:
    return bool(_legacy_import_category(imported, file_path))


def _owner_for_route(route_file: str, path: str) -> str:
    normalized = path.strip()
    if route_file.endswith("chat_api.py"):
        return "MOVE_TO_CHAT_API_LATER"
    if route_file.endswith("web_api.py"):
        if normalized.startswith("/chat"):
            return "MOVE_TO_CHAT_API_LATER"
        if normalized.startswith("/mobile"):
            return "DEPRECATED_KEEP_COMPAT"
        if normalized.startswith("/api/mobile"):
            return "DEPRECATED_KEEP_COMPAT"
        dedicated_prefixes = (
            "/api/debug",
            "/api/auth",
            "/api/contacts",
            "/api/ui",
            "/api/local-actions",
            "/api/windows",
            "/api/knowledge",
            "/api/screen",
            "/api/window",
            "/api/context",
            "/api/voice",
            "/api/settings",
        )
        if normalized.startswith(dedicated_prefixes):
            return "MOVE_TO_DEDICATED_ROUTER_LATER"
        return "KEEP_IN_WEB_API"
    return "UNKNOWN_NEEDS_REVIEW"


def scan_python_files() -> list[PythonFileInfo]:
    files: list[PythonFileInfo] = []
    for path in sorted(BACKEND_APP.rglob("*.py")):
        text = _read_text(path)
        marker_lines = []
        for index, line in enumerate(text.splitlines(), start=1):
            if MARKER_PATTERN.search(line):
                marker_lines.append((index, line.strip()))
        files.append(
            PythonFileInfo(
                path=path,
                rel_path=_rel(path),
                module=_module_name(path),
                line_count=_line_count(text),
                marker_lines=tuple(marker_lines),
            )
        )
    return files


def scan_imports(files: list[PythonFileInfo]) -> list[ImportInfo]:
    imports: list[ImportInfo] = []
    for info in files:
        try:
            tree = ast.parse(_read_text(info.path), filename=str(info.path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name
                    imports.append(
                        ImportInfo(
                            file=info.rel_path,
                            module=info.module,
                            imported=imported,
                            kind="import",
                            line=getattr(node, "lineno", 0),
                            legacy_risk=_is_legacy_import(imported, info.rel_path),
                            legacy_category=_legacy_import_category(imported, info.rel_path),
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                base = "." * int(node.level or 0) + (node.module or "")
                for alias in node.names:
                    imported = f"{base}.{alias.name}" if base else alias.name
                    imports.append(
                        ImportInfo(
                            file=info.rel_path,
                            module=info.module,
                            imported=imported,
                            kind="from",
                            line=getattr(node, "lineno", 0),
                            legacy_risk=_is_legacy_import(imported, info.rel_path),
                            legacy_category=_legacy_import_category(imported, info.rel_path),
                        )
                    )
    return imports


def scan_generated_artifact_legacy_paths() -> list[str]:
    candidates = []
    legacy_roots = [
        BACKEND_APP / "brain",
        BACKEND_APP / "services" / "integrations",
        BACKEND_APP / "services" / "iot",
        BACKEND_APP / "services" / "llm",
        BACKEND_APP / "core" / "knowledge_engine",
        BACKEND_APP / "core" / "math_engine",
        BACKEND_APP / "core" / "security",
    ]
    for root in legacy_roots:
        if not root.exists():
            continue
        source_files = [path for path in root.rglob("*.py") if "__pycache__" not in path.parts]
        pycache_files = list(root.rglob("*.pyc"))
        if pycache_files and not source_files:
            candidates.append(_rel(root))
    return sorted(candidates)


def scan_routes(files: list[PythonFileInfo]) -> list[RouteInfo]:
    routes: list[RouteInfo] = []
    for info in files:
        try:
            tree = ast.parse(_read_text(info.path), filename=str(info.path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                route = _decorator_route(decorator)
                if route is None:
                    continue
                methods, path = route
                for method in methods:
                    routes.append(
                        RouteInfo(
                            file=info.rel_path,
                            module=info.module,
                            method=method,
                            path=path,
                            function=node.name,
                            line=getattr(node, "lineno", 0),
                            owner_recommendation=_owner_for_route(info.rel_path, path),
                        )
                    )
    return sorted(routes, key=lambda item: (item.path, item.method, item.file, item.line))


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        text = str(value)
        text = text.replace("|", "\\|").replace("\n", "<br>")
        return text

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell(value) for value in row) + " |")
    return "\n".join(lines)


def _duplicate_routes(routes: list[RouteInfo]) -> dict[tuple[str, str], list[RouteInfo]]:
    groups: dict[tuple[str, str], list[RouteInfo]] = defaultdict(list)
    for route in routes:
        groups[(route.method, route.path)].append(route)
    return {key: value for key, value in groups.items() if len(value) > 1}


def _route_path_overlaps(routes: list[RouteInfo]) -> dict[str, list[RouteInfo]]:
    groups: dict[str, list[RouteInfo]] = defaultdict(list)
    for route in routes:
        groups[route.path].append(route)
    return {key: value for key, value in groups.items() if len(value) > 1}


def _focus_file_rows(files: list[PythonFileInfo], imports: list[ImportInfo], routes: list[RouteInfo]) -> list[list[Any]]:
    by_rel = {info.rel_path: info for info in files}
    import_counts = Counter(item.file for item in imports)
    route_counts = Counter(item.file for item in routes)
    rows: list[list[Any]] = []
    focus_paths = dict(FOCUS_FILES)
    for provider_file in sorted(PROVIDER_DIR.glob("*.py")):
        focus_paths[f"terminal_provider:{provider_file.stem}"] = provider_file
    for label, path in focus_paths.items():
        rel = _rel(path)
        info = by_rel.get(rel)
        if info is None:
            rows.append([label, rel, "MISSING", "", "", ""])
            continue
        rows.append([label, rel, info.line_count, import_counts[rel], route_counts[rel], len(info.marker_lines)])
    return rows


def write_backend_files(files: list[PythonFileInfo]) -> None:
    large = [info for info in files if info.line_count > 500]
    marker_files = [info for info in files if info.marker_lines]
    rows = [[info.rel_path, info.module, info.line_count, len(info.marker_lines)] for info in files]
    large_rows = [[info.rel_path, info.line_count] for info in sorted(large, key=lambda item: item.line_count, reverse=True)]
    marker_rows = []
    for info in marker_files:
        preview = "; ".join(f"{line}: {text[:120]}" for line, text in info.marker_lines[:5])
        marker_rows.append([info.rel_path, len(info.marker_lines), preview])
    content = [
        "# Backend Files Inventory",
        "",
        f"Scanned `{BACKEND_APP.relative_to(PROJECT_ROOT).as_posix()}`.",
        "",
        f"- Python files: {len(files)}",
        f"- Large files over 500 lines: {len(large)}",
        f"- Files with TODO/FIXME/deprecated markers: {len(marker_files)}",
        "",
        "## All Python Files",
        "",
        _md_table(["File", "Module", "Lines", "Markers"], rows),
        "",
        "## Large Files Over 500 Lines",
        "",
        _md_table(["File", "Lines"], large_rows),
        "",
        "## Marker Files",
        "",
        _md_table(["File", "Marker Count", "Preview"], marker_rows),
        "",
    ]
    (INVENTORY_DIR / "BACKEND_FILES.md").write_text("\n".join(content), encoding="utf-8")


def write_api_routes(routes: list[RouteInfo]) -> None:
    duplicates = _duplicate_routes(routes)
    path_overlaps = _route_path_overlaps(routes)
    rows = [
        [route.method, route.path, route.function, route.module, route.file, route.line, route.owner_recommendation]
        for route in routes
    ]
    duplicate_rows = []
    for (method, path), items in sorted(duplicates.items(), key=lambda item: (item[0][1], item[0][0])):
        duplicate_rows.append([method, path, "<br>".join(f"{item.file}:{item.line} `{item.function}`" for item in items)])
    overlap_rows = []
    for path, items in sorted(path_overlaps.items()):
        methods = ", ".join(sorted({item.method for item in items}))
        locations = "<br>".join(f"{item.method} {item.file}:{item.line} `{item.function}`" for item in items)
        overlap_rows.append([path, methods, locations])
    by_owner = Counter(route.owner_recommendation for route in routes)
    owner_rows = [[owner, count] for owner, count in sorted(by_owner.items())]
    content = [
        "# API Routes Inventory",
        "",
        f"- Route declarations: {len(routes)}",
        f"- Exact duplicate method/path candidates: {len(duplicates)}",
        f"- Duplicate path candidates across methods/modules: {len(path_overlaps)}",
        "",
        "## Ownership Recommendation Counts",
        "",
        _md_table(["Recommendation", "Route Count"], owner_rows),
        "",
        "## All Routes",
        "",
        _md_table(["Method", "Path", "Function", "Module", "File", "Line", "Ownership"], rows),
        "",
        "## Exact Duplicate Method/Path Candidates",
        "",
        _md_table(["Method", "Path", "Locations"], duplicate_rows),
        "",
        "## Duplicate Path Candidates",
        "",
        _md_table(["Path", "Methods", "Locations"], overlap_rows),
        "",
    ]
    (INVENTORY_DIR / "API_ROUTES.md").write_text("\n".join(content), encoding="utf-8")


def write_import_graph(files: list[PythonFileInfo], imports: list[ImportInfo], routes: list[RouteInfo]) -> None:
    rows = [[item.file, item.line, item.kind, item.imported, item.legacy_category] for item in imports]
    legacy_rows = [[item.file, item.line, item.kind, item.imported, item.legacy_category] for item in imports if item.legacy_risk]
    category_counts = Counter(item.legacy_category or "NO_LEGACY_RISK" for item in imports)
    category_rows = [[category, count] for category, count in sorted(category_counts.items())]
    generated_artifacts = scan_generated_artifact_legacy_paths()
    generated_rows = [[path, "GENERATED_ARTIFACT_ONLY"] for path in generated_artifacts]
    focus_rows = _focus_file_rows(files, imports, routes)
    most_imports = Counter(item.file for item in imports).most_common(20)
    most_rows = [[file, count] for file, count in most_imports]
    content = [
        "# Import Graph Inventory",
        "",
        f"- Import statements/items: {len(imports)}",
        f"- Legacy `modules` / `features.modules` import risks: {len(legacy_rows)}",
        f"- External legacy import risks: {sum(1 for item in imports if item.legacy_category == 'NEEDS_RUNTIME_REVIEW')}",
        f"- Compatibility shim imports kept now: {sum(1 for item in imports if item.legacy_category == 'KEEP_COMPAT_NOW')}",
        f"- Generated artifact-only legacy paths: {len(generated_artifacts)}",
        "",
        "## Legacy Import Categories",
        "",
        _md_table(["Category", "Import Count"], category_rows),
        "",
        "## Focus Module Comparison",
        "",
        _md_table(["Area", "File", "Lines", "Imports", "Routes", "Markers"], focus_rows),
        "",
        "## Files With Most Imports",
        "",
        _md_table(["File", "Import Count"], most_rows),
        "",
        "## Legacy Import Risks",
        "",
        _md_table(["File", "Line", "Kind", "Imported", "Category"], legacy_rows),
        "",
        "## Generated Artifact-Only Legacy Paths",
        "",
        _md_table(["Path", "Category"], generated_rows),
        "",
        "## All Imports",
        "",
        _md_table(["File", "Line", "Kind", "Imported", "Legacy Category"], rows),
        "",
    ]
    (INVENTORY_DIR / "IMPORT_GRAPH.md").write_text("\n".join(content), encoding="utf-8")


def write_duplication_risks(files: list[PythonFileInfo], imports: list[ImportInfo], routes: list[RouteInfo]) -> None:
    duplicates = _duplicate_routes(routes)
    path_overlaps = _route_path_overlaps(routes)
    by_rel = {info.rel_path: info for info in files}
    focus_rows = _focus_file_rows(files, imports, routes)
    large_rows = [
        [info.rel_path, info.line_count]
        for info in sorted(files, key=lambda item: item.line_count, reverse=True)
        if info.line_count > 500
    ][:20]
    duplicate_rows = []
    for (method, path), items in sorted(duplicates.items(), key=lambda item: (item[0][1], item[0][0])):
        duplicate_rows.append([method, path, "<br>".join(f"{item.file}:{item.line} `{item.function}`" for item in items)])
    overlap_rows = []
    for path, items in sorted(path_overlaps.items()):
        if path in {key[1] for key in duplicates}:
            continue
        overlap_rows.append([path, "<br>".join(f"{item.method} {item.file}:{item.line} `{item.function}`" for item in items)])
    comparison_notes = [
        ["web_api.py vs chat_api.py", "DUPLICATE", "Both define FastAPI apps and overlapping chat/auth/runtime surfaces. Keep runtime stable; document route ownership before moving routes."],
        ["terminal chatbot providers vs shared llm_client", "DUPLICATE", "Terminal chatbot has OpenAI/Gemini/Ollama/fallback providers. Shared web chat client has OpenAI/Ollama plus fallback behavior through local knowledge and error paths."],
        ["memory/database modules", "DUPLICATE", "Assistant memory DB, productivity scope store, and terminal chat DB are separate. Do not merge without migration design."],
        ["command_router.py", "PARTIAL", "Large central command dispatcher. Refactor only after route/import inventory and domain-specific tests are in place."],
        ["features/modules", "DUPLICATE", "Compatibility aliases for legacy imports. Keep until all legacy import users are migrated."],
    ]
    route_file_rows = []
    for key in ("web_api", "chat_api", "command_router", "unified_command_router"):
        path = FOCUS_FILES[key]
        rel = _rel(path)
        info = by_rel.get(rel)
        route_file_rows.append([key, rel, info.line_count if info else "MISSING", sum(1 for route in routes if route.file == rel)])
    content = [
        "# Duplication Risks",
        "",
        "This report identifies candidates for later cleanup. It does not authorize moving or deleting code.",
        "",
        "## High-Level Risks",
        "",
        _md_table(["Area", "Status", "Recommendation"], comparison_notes),
        "",
        "## Focus File Sizes And Route Counts",
        "",
        _md_table(["Area", "File", "Lines", "Routes"], route_file_rows),
        "",
        "## Focus Module Comparison",
        "",
        _md_table(["Area", "File", "Lines", "Imports", "Routes", "Markers"], focus_rows),
        "",
        "## Exact Duplicate Method/Path Routes",
        "",
        _md_table(["Method", "Path", "Locations"], duplicate_rows),
        "",
        "## Same Path Across Multiple Declarations",
        "",
        _md_table(["Path", "Locations"], overlap_rows),
        "",
        "## Largest Files",
        "",
        _md_table(["File", "Lines"], large_rows),
        "",
    ]
    (INVENTORY_DIR / "DUPLICATION_RISKS.md").write_text("\n".join(content), encoding="utf-8")


def write_api_ownership_plan(routes: list[RouteInfo]) -> None:
    grouped: dict[str, list[RouteInfo]] = defaultdict(list)
    for route in routes:
        grouped[route.owner_recommendation].append(route)
    sections = []
    for recommendation in [
        "KEEP_IN_WEB_API",
        "MOVE_TO_CHAT_API_LATER",
        "MOVE_TO_DEDICATED_ROUTER_LATER",
        "DEPRECATED_KEEP_COMPAT",
        "UNKNOWN_NEEDS_REVIEW",
    ]:
        items = sorted(grouped.get(recommendation, []), key=lambda item: (item.path, item.method, item.file))
        rows = [[item.method, item.path, item.function, item.file, item.line] for item in items]
        sections.extend([
            f"## {recommendation}",
            "",
            _md_table(["Method", "Path", "Function", "File", "Line"], rows),
            "",
        ])
    guidance = [
        "# API Ownership Plan",
        "",
        "This is a read-only classification generated from route inventory heuristics. It is a planning document, not a code movement instruction.",
        "",
        "## Recommendation Meanings",
        "",
        _md_table(
            ["Status", "Meaning"],
            [
                ["KEEP_IN_WEB_API", "Keep in `backend/app/api/web_api.py` for the active desktop backend runtime."],
                ["MOVE_TO_CHAT_API_LATER", "Candidate to move or consolidate into the chat API after contracts and tests are explicit."],
                ["MOVE_TO_DEDICATED_ROUTER_LATER", "Candidate for a future domain router such as auth, debug, voice, contacts, UI analysis, or context."],
                ["DEPRECATED_KEEP_COMPAT", "Keep for compatibility. Do not remove without replacement clients and migration notes."],
                ["UNKNOWN_NEEDS_REVIEW", "Route could not be classified safely by this inventory script."],
            ],
        ),
        "",
        "## Current Recommendation",
        "",
        "Keep `backend/app/api/web_api.py` as the active desktop backend API owner for now. Treat `backend/app/api/chat_api.py` as a candidate chat-focused surface that needs explicit ownership before any consolidation.",
        "",
        "## Phase 1 Duplicate Route Decisions",
        "",
        "The active desktop backend entrypoint imports `backend/app/api/web_api.py`. The duplicate declarations in `backend/app/api/chat_api.py` are registered only on the alternate `chat_api.app`, not on the active desktop app object.",
        "",
        _md_table(
            ["Route", "Active Owner", "Secondary Declaration", "Decision", "Future Action"],
            [
                [
                    item["route"],
                    item["active_owner"],
                    item["secondary"],
                    item["decision"],
                    item["future_action"],
                ]
                for item in DUPLICATE_ROUTE_DECISIONS
            ],
        ),
        "",
    ]
    (DOCS_DIR / "API_OWNERSHIP_PLAN.md").write_text("\n".join(guidance + sections), encoding="utf-8")


def main() -> int:
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
    files = scan_python_files()
    imports = scan_imports(files)
    routes = scan_routes(files)
    write_backend_files(files)
    write_api_routes(routes)
    write_import_graph(files, imports, routes)
    write_duplication_risks(files, imports, routes)
    write_api_ownership_plan(routes)

    duplicates = _duplicate_routes(routes)
    large_files = sorted((info for info in files if info.line_count > 500), key=lambda item: item.line_count, reverse=True)
    legacy_imports = [item for item in imports if item.legacy_risk]
    category_counts = Counter(item.legacy_category or "NO_LEGACY_RISK" for item in imports)
    generated_artifacts = scan_generated_artifact_legacy_paths()
    print(f"backend_files={len(files)}")
    print(f"route_count={len(routes)}")
    print(f"duplicate_method_path_risks={len(duplicates)}")
    print(f"large_files_over_500={len(large_files)}")
    print(f"legacy_import_risks={len(legacy_imports)}")
    print(
        "legacy_import_categories="
        + ", ".join(f"{category}:{count}" for category, count in sorted(category_counts.items()))
    )
    print(f"generated_artifact_only_legacy_paths={len(generated_artifacts)}")
    print("largest_files=" + ", ".join(f"{item.rel_path}:{item.line_count}" for item in large_files[:5]))
    print(f"reports_dir={INVENTORY_DIR.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"api_ownership_plan={(DOCS_DIR / 'API_OWNERSHIP_PLAN.md').relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
