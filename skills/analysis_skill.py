from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
    "out",
    "coverage",
}

DEFAULT_EXCLUDE_FILES = {
    ".DS_Store",
}

TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".scss",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
}

LANGUAGE_GROUPS = {
    "python": {".py"},
    "javascript": {".js", ".jsx"},
    "typescript": {".ts", ".tsx"},
    "shell": {".sh", ".ps1", ".bat", ".cmd"},
    "markdown": {".md"},
    "json": {".json"},
    "yaml": {".yaml", ".yml"},
    "toml": {".toml"},
    "html": {".html"},
    "css": {".css", ".scss"},
    "go": {".go"},
    "rust": {".rs"},
    "java": {".java"},
    "kotlin": {".kt"},
    "cpp": {".c", ".cpp", ".h", ".hpp"},
    "csharp": {".cs"},
}

TODO_PATTERN = re.compile(r"(#\s*(TODO|FIXME))|\b(TODO|FIXME):")
ABS_PATH_PATTERN = re.compile(r"([A-Za-z]:\\\\|/root/|/home/|/Users/)")


@dataclass
class AnalysisConfig:
    root: Path
    max_files: int = 20000
    max_file_size_bytes: int = 1_500_000
    max_line_scan: int = 2000
    max_todo_matches: int = 200
    max_largest_files: int = 20
    max_entrypoints: int = 30
    max_scan_seconds: Optional[float] = None
    include_logs: bool = False
    exclude_dirs: Iterable[str] = field(default_factory=lambda: sorted(DEFAULT_EXCLUDE_DIRS))
    exclude_files: Iterable[str] = field(default_factory=lambda: sorted(DEFAULT_EXCLUDE_FILES))


@dataclass
class AnalysisReport:
    root: str
    generated_at: str
    truncated: bool
    summary: Dict[str, object]
    extensions: Dict[str, int]
    language_summary: Dict[str, int]
    largest_files: List[Dict[str, object]]
    top_directories: List[Dict[str, object]]
    entrypoints: List[Dict[str, object]]
    todos: List[Dict[str, object]]
    missing_tests: List[Dict[str, object]]
    dependencies: Dict[str, object]
    test_coverage: Dict[str, object]
    dependency_summary: Dict[str, object]
    scan_stats: Dict[str, object]
    risks: List[str]
    notes: List[str]


def _is_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    try:
        with path.open("rb") as handle:
            chunk = handle.read(4096)
        if b"\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except Exception:
        return False


def _language_for_extension(ext: str) -> str:
    for name, extensions in LANGUAGE_GROUPS.items():
        if ext in extensions:
            return name
    return "other"


def _collect_test_paths(root: Path) -> Tuple[List[Path], Dict[str, Path]]:
    candidates = []
    for name in ("tests", "test", "__tests__", "imp/tests"):
        path = root / name
        if path.exists() and path.is_dir():
            candidates.append(path)
    imp_tests = root / "imp" / "tests"
    if imp_tests.exists() and imp_tests.is_dir() and imp_tests not in candidates:
        candidates.append(imp_tests)
    test_files: Dict[str, Path] = {}
    for tests_dir in candidates:
        for file in tests_dir.rglob("test*.py"):
            test_files[file.name.lower()] = file
    return candidates, test_files


def _candidate_test_names(stem: str) -> List[str]:
    if stem.startswith("test"):
        return []
    base = stem.replace("-", "_")
    names = {
        f"test_{base}.py",
        f"test-{stem}.py",
        f"{base}_test.py",
        f"{stem}-test.py",
    }
    return sorted(names)


def _summarize_dependencies(root: Path) -> Dict[str, object]:
    deps: Dict[str, object] = {}
    requirements = root / "requirements.txt"
    if requirements.exists():
        items = []
        for line in requirements.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            items.append(line)
        deps["requirements.txt"] = items
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        deps["pyproject.toml"] = "present"
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            deps["package.json"] = {
                "dependencies": sorted((data.get("dependencies") or {}).keys()),
                "devDependencies": sorted((data.get("devDependencies") or {}).keys()),
            }
        except Exception:
            deps["package.json"] = "unreadable"
    cargo = root / "Cargo.toml"
    if cargo.exists():
        deps["Cargo.toml"] = "present"
    return deps


def _collect_python_imports(path: Path) -> List[str]:
    imports: List[str] = []
    try:
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("import "):
                parts = line.split()
                if len(parts) >= 2:
                    imports.append(parts[1].split(".")[0])
            elif line.startswith("from "):
                parts = line.split()
                if len(parts) >= 2:
                    imports.append(parts[1].split(".")[0])
    except Exception:
        return []
    return imports


def _summarize_test_coverage(root: Path, tests_dir: Path, sources: List[Path]) -> Dict[str, object]:
    total = 0
    covered = 0
    missing: List[str] = []
    referenced_files: set[str] = set()

    if tests_dir.exists():
        pattern = re.compile(r"imp-[A-Za-z0-9_-]+\.py")
        for test_file in tests_dir.rglob("*.py"):
            try:
                text = test_file.read_text(errors="ignore")
            except Exception:
                continue
            for match in pattern.findall(text):
                referenced_files.add(match)

    for src in sources:
        if src.suffix.lower() != ".py":
            continue
        total += 1
        if src.name in referenced_files:
            covered += 1
            continue
        candidates = _candidate_test_names(src.stem)
        if candidates:
            for candidate in candidates:
                if (tests_dir / candidate).exists():
                    covered += 1
                    break
            else:
                missing.append(str(src.relative_to(root)))

    coverage = round((covered / total) * 100, 2) if total else 100.0
    return {
        "total_modules": total,
        "covered_modules": covered,
        "coverage_percent": coverage,
        "referenced_modules": len(referenced_files),
        "missing_tests": missing[:200],
    }


def analyze_repository(config: AnalysisConfig) -> AnalysisReport:
    start_time = time.monotonic()
    root = config.root.resolve()
    excluded_dirs = set(config.exclude_dirs)
    excluded_files = set(config.exclude_files)

    file_count = 0
    dir_count = 0
    total_bytes = 0
    extensions: Dict[str, int] = {}
    language_summary: Dict[str, int] = {}
    largest_files: List[Tuple[int, Path]] = []
    todos: List[Dict[str, object]] = []
    abs_path_hits = 0

    tests_dirs, test_files = _collect_test_paths(root)
    missing_tests: List[Dict[str, object]] = []
    test_lookup = set(test_files.keys())

    entrypoints: List[Dict[str, object]] = []
    truncated = False

    python_imports: Dict[str, int] = {}
    dir_stats: Dict[str, Dict[str, int]] = {}
    skipped_large = 0
    skipped_binary = 0
    skipped_unreadable = 0
    skipped_symlink = 0
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dir_count += 1

        pruned = []
        for name in list(dirnames):
            if name in excluded_dirs:
                continue
            if not config.include_logs and name == "logs":
                continue
            pruned.append(name)
        dirnames[:] = pruned

        for filename in filenames:
            if filename in excluded_files:
                continue
            if config.max_scan_seconds is not None:
                elapsed = time.monotonic() - start_time
                if elapsed > config.max_scan_seconds:
                    truncated = True
                    break
            if file_count >= config.max_files:
                truncated = True
                break
            path = current / filename
            try:
                if path.is_symlink():
                    skipped_symlink += 1
                    continue
                stat = path.stat()
            except FileNotFoundError:
                continue
            except OSError:
                skipped_unreadable += 1
                continue
            file_count += 1
            total_bytes += stat.st_size
            ext = path.suffix.lower() or "<none>"
            extensions[ext] = extensions.get(ext, 0) + 1
            language = _language_for_extension(ext)
            language_summary[language] = language_summary.get(language, 0) + 1

            rel = path.relative_to(root)
            top_dir = rel.parts[0] if len(rel.parts) > 1 else "."
            stats = dir_stats.setdefault(top_dir, {"files": 0, "bytes": 0})
            stats["files"] += 1
            stats["bytes"] += stat.st_size

            if stat.st_size > 0:
                largest_files.append((stat.st_size, path))

            if stat.st_size > config.max_file_size_bytes:
                skipped_large += 1
                continue

            if not _is_text_file(path):
                skipped_binary += 1
                continue

            try:
                lines = path.read_text(errors="ignore").splitlines()
            except Exception:
                skipped_unreadable += 1
                continue

            for lineno, line in enumerate(lines[: config.max_line_scan], 1):
                if ABS_PATH_PATTERN.search(line):
                    abs_path_hits += 1
                if TODO_PATTERN.search(line):
                    if len(todos) < config.max_todo_matches:
                        todos.append(
                            {
                                "path": str(path.relative_to(root)),
                                "line": lineno,
                                "text": line.strip()[:160],
                            }
                        )

            if path.suffix.lower() == ".py":
                if "tests" not in rel.parts:
                    for candidate in _candidate_test_names(path.stem):
                        if candidate.lower() in test_lookup:
                            break
                    else:
                        missing_tests.append(
                            {
                                "path": str(rel),
                                "suggested_tests": _candidate_test_names(path.stem),
                            }
                        )
                for name in _collect_python_imports(path):
                    python_imports[name] = python_imports.get(name, 0) + 1

            if len(entrypoints) < config.max_entrypoints:
                if path.suffix.lower() in {".sh", ".ps1", ".py"}:
                    if "bin" in path.parts or "scripts" in path.parts:
                        entrypoints.append(
                            {
                                "path": str(path.relative_to(root)),
                                "type": "script",
                            }
                        )
                    elif path.suffix.lower() == ".py":
                        if "__main__" in "\n".join(lines[:50]):
                            entrypoints.append(
                                {
                                    "path": str(path.relative_to(root)),
                                    "type": "python-main",
                                }
                            )
                elif lines:
                    shebang = lines[0].startswith("#!")
                    if shebang:
                        entrypoints.append(
                            {
                                "path": str(path.relative_to(root)),
                                "type": "shebang",
                            }
                        )

        if truncated:
            break

    largest_files_sorted = sorted(largest_files, key=lambda item: item[0], reverse=True)
    largest_files_report = [
        {
            "path": str(path.relative_to(root)),
            "bytes": size,
        }
        for size, path in largest_files_sorted[: config.max_largest_files]
    ]
    top_directories = [
        {"path": name, "files": stats["files"], "bytes": stats["bytes"]}
        for name, stats in sorted(
            dir_stats.items(), key=lambda item: item[1]["files"], reverse=True
        )[:10]
    ]

    risks = []
    if abs_path_hits:
        risks.append(f"Found {abs_path_hits} potential absolute path references.")
    if truncated:
        risks.append("File scan was truncated due to max_files limit.")
    if not tests_dirs:
        risks.append("No tests directory detected by heuristic.")

    summary = {
        "files": file_count,
        "directories": dir_count,
        "total_bytes": total_bytes,
        "tests_dirs": [str(path.relative_to(root)) for path in tests_dirs],
    }
    scan_stats = {
        "elapsed_seconds": round(time.monotonic() - start_time, 2),
        "skipped_large": skipped_large,
        "skipped_binary": skipped_binary,
        "skipped_unreadable": skipped_unreadable,
        "skipped_symlink": skipped_symlink,
    }

    dependency_summary = {
        "top_python_imports": sorted(
            python_imports.items(), key=lambda item: item[1], reverse=True
        )[:20]
    }
    code_root = root / "imp" if (root / "imp").exists() else root
    sources = [
        path
        for path in code_root.rglob("*.py")
        if "tests" not in path.parts
        and "logs" not in path.parts
        and "__pycache__" not in path.parts
    ]
    preferred_tests = root / "imp" / "tests"
    tests_root = preferred_tests if preferred_tests.exists() else (tests_dirs[0] if tests_dirs else root / "tests")
    test_coverage = _summarize_test_coverage(
        root, tests_root, sources
    )
    report = AnalysisReport(
        root=str(root),
        generated_at=datetime.now(timezone.utc).isoformat(),
        truncated=truncated,
        summary=summary,
        extensions=dict(sorted(extensions.items(), key=lambda item: item[1], reverse=True)),
        language_summary=dict(
            sorted(language_summary.items(), key=lambda item: item[1], reverse=True)
        ),
        largest_files=largest_files_report,
        top_directories=top_directories,
        entrypoints=entrypoints,
        todos=todos,
        missing_tests=missing_tests[: config.max_todo_matches],
        dependencies=_summarize_dependencies(root),
        test_coverage=test_coverage,
        dependency_summary=dependency_summary,
        scan_stats=scan_stats,
        risks=risks,
        notes=[],
    )
    return report


def _default_output_paths(root: Path) -> Tuple[Path, Path]:
    logs_dir = root / "imp" / "logs"
    if logs_dir.exists():
        return logs_dir / "imp-analysis-report.json", logs_dir / "imp-analysis-report.md"
    return root / "analysis-report.json", root / "analysis-report.md"


def _render_markdown(report: AnalysisReport) -> str:
    lines = []
    lines.append("# Repository Analysis Report")
    lines.append("")
    lines.append(f"Root: `{report.root}`")
    lines.append(f"Generated: `{report.generated_at}`")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Files: {report.summary.get('files')}")
    lines.append(f"- Directories: {report.summary.get('directories')}")
    lines.append(f"- Total bytes: {report.summary.get('total_bytes')}")
    tests_dirs = report.summary.get("tests_dirs") or []
    lines.append(f"- Test dirs: {', '.join(tests_dirs) if tests_dirs else 'None detected'}")
    lines.append("")
    lines.append("## Top Extensions")
    for ext, count in list(report.extensions.items())[:12]:
        lines.append(f"- `{ext}`: {count}")
    lines.append("")
    if report.language_summary:
        lines.append("## Language Summary")
        for name, count in report.language_summary.items():
            lines.append(f"- `{name}`: {count}")
        lines.append("")
    lines.append("## Largest Files")
    for item in report.largest_files:
        lines.append(f"- `{item['path']}` ({item['bytes']} bytes)")
    lines.append("")
    if report.top_directories:
        lines.append("## Top Directories")
        for item in report.top_directories:
            lines.append(f"- `{item['path']}`: {item['files']} files, {item['bytes']} bytes")
        lines.append("")
    lines.append("## Entry Points")
    for item in report.entrypoints:
        lines.append(f"- `{item['path']}` ({item['type']})")
    lines.append("")
    if report.todos:
        lines.append("## TODO / FIXME")
        for item in report.todos[:20]:
            lines.append(f"- `{item['path']}`:{item['line']} {item['text']}")
        if len(report.todos) > 20:
            lines.append(f"- ... {len(report.todos) - 20} more")
        lines.append("")
    if report.missing_tests:
        lines.append("## Missing Tests (Heuristic)")
        for item in report.missing_tests[:20]:
            lines.append(f"- `{item['path']}`")
        if len(report.missing_tests) > 20:
            lines.append(f"- ... {len(report.missing_tests) - 20} more")
        lines.append("")
    if report.dependencies:
        lines.append("## Dependencies")
        for key, value in report.dependencies.items():
            if isinstance(value, list):
                lines.append(f"- `{key}`: {len(value)} entries")
            else:
                lines.append(f"- `{key}`: {value}")
        lines.append("")
    if report.test_coverage:
        lines.append("## Test Coverage")
        lines.append(
            f"- Modules covered: {report.test_coverage.get('covered_modules')}/{report.test_coverage.get('total_modules')}"
        )
        lines.append(f"- Coverage: {report.test_coverage.get('coverage_percent')}%")
        lines.append(f"- Referenced modules: {report.test_coverage.get('referenced_modules')}")
        lines.append("")
    if report.dependency_summary:
        lines.append("## Top Python Imports")
        for name, count in report.dependency_summary.get("top_python_imports", []):
            lines.append(f"- `{name}`: {count}")
        lines.append("")
    if report.scan_stats:
        lines.append("## Scan Stats")
        lines.append(f"- Elapsed seconds: {report.scan_stats.get('elapsed_seconds')}")
        lines.append(f"- Skipped large files: {report.scan_stats.get('skipped_large')}")
        lines.append(f"- Skipped binary files: {report.scan_stats.get('skipped_binary')}")
        lines.append(f"- Skipped unreadable files: {report.scan_stats.get('skipped_unreadable')}")
        lines.append(f"- Skipped symlinks: {report.scan_stats.get('skipped_symlink')}")
        lines.append("")
    if report.risks:
        lines.append("## Risks")
        for risk in report.risks:
            lines.append(f"- {risk}")
        lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a repository and emit a structured report.")
    parser.add_argument("root", nargs="?", default=".", help="Repository root")
    parser.add_argument("--include-logs", action="store_true", help="Include logs directory")
    parser.add_argument("--max-files", type=int, default=20000)
    parser.add_argument("--max-file-size", type=int, default=1_500_000)
    parser.add_argument("--max-seconds", type=float, default=None)
    parser.add_argument("--json-out", type=str, default=None)
    parser.add_argument("--md-out", type=str, default=None)
    args = parser.parse_args(argv)

    root = Path(args.root)
    config = AnalysisConfig(
        root=root,
        max_files=args.max_files,
        max_file_size_bytes=args.max_file_size,
        max_scan_seconds=args.max_seconds,
        include_logs=args.include_logs,
    )
    report = analyze_repository(config)
    json_out, md_out = _default_output_paths(root)
    if args.json_out:
        json_out = Path(args.json_out)
    if args.md_out:
        md_out = Path(args.md_out)

    json_out.write_text(json.dumps(report.__dict__, indent=2))
    md_out.write_text(_render_markdown(report))
    print(f"Report written to {json_out}")
    print(f"Markdown summary written to {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
