from __future__ import annotations
import ast
import json
from pathlib import Path
import re
from typing import Iterable


def generate_code_map() -> Path:
    """Scan the project and record imports, variables, functions and classes."""
    root = Path(__file__).resolve().parents[2]
    code_dir = root / "imp"
    code_map = {}
    for py_file in code_dir.rglob("*.py"):
        if "logs" in py_file.relative_to(code_dir).parts:
            continue
        try:
            tree = ast.parse(py_file.read_text())
            imports: set[str] = set()
            variables: set[str] = set()
            funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
            classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                    else:
                        for alias in node.names:
                            imports.add(alias.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            variables.add(target.id)
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name):
                        variables.add(node.target.id)
            rel = py_file.relative_to(root)
            code_map[rel.as_posix()] = {
                "imports": sorted(imports),
                "variables": sorted(variables),
                "functions": funcs,
                "classes": classes,
            }
        except Exception as exc:
            rel = py_file.relative_to(root)
            code_map[rel.as_posix()] = {"error": str(exc)}
    log_dir = root / "imp" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    out_path = log_dir / "imp-code-map.json"
    out_path.write_text(json.dumps(code_map, indent=2))
    return out_path


def _candidate_test_paths(src: Path, tests_dir: Path) -> Iterable[Path]:
    """Generate plausible test-file paths for ``src``.

    Many IMP modules drop the ``imp`` prefix or swap hyphens for underscores
    when naming their tests. The previous implementation only checked a single
    filename pattern, so valid tests were marked as missing. By exploring a
    richer set of name variants we keep the analyzer accurate.
    """

    stem = src.stem
    if stem == "__init__":
        return []

    base_names = {stem}
    for prefix in ("imp-", "imp_"):
        if stem.startswith(prefix):
            base_names.add(stem[len(prefix) :])

    expanded = set(base_names)
    for name in list(base_names):
        expanded.add(name.replace("-", "_"))
        expanded.add(name.replace("_", "-"))
        if "neural-network" in name:
            expanded.add(name.replace("neural-network", "network"))
        if "neural_network" in name:
            expanded.add(name.replace("neural_network", "network"))

    return [tests_dir / f"test-{name}.py" for name in expanded if name]


TODO_PATTERN = re.compile(r"(#\s*(TODO|FIXME))|\b(TODO|FIXME):")


def analyze_code_map(code_map_path: Path | None = None) -> Path:
    """Read the code map and record simple weaknesses for each module.

    Weaknesses include modules missing a corresponding test file and lines
    containing TODO or FIXME comments. The results are written to
    ``imp-code-map-analysis.json`` for later goal generation.
    """
    root = Path(__file__).resolve().parents[2]
    if code_map_path is None:
        code_map_path = root / "imp" / "logs" / "imp-code-map.json"
    data = json.loads(code_map_path.read_text())
    analysis: dict[str, dict] = {}
    tests_dir = root / "imp" / "tests"
    for rel in data.keys():
        src = root / rel
        issues: dict[str, object] = {}
        test_candidates = list(_candidate_test_paths(src, tests_dir))
        if test_candidates and not any(path.exists() for path in test_candidates):
            issues["missing_test"] = True
        todos = []
        try:
            for lineno, line in enumerate(src.read_text().splitlines(), 1):
                if TODO_PATTERN.search(line):
                    todos.append({"line": lineno, "text": line.strip()})
        except FileNotFoundError:
            issues["missing_source"] = True
        if todos:
            issues["todos"] = todos
        if issues:
            analysis[rel] = issues
    out_path = root / "imp" / "logs" / "imp-code-map-analysis.json"
    out_path.write_text(json.dumps(analysis, indent=2))
    return out_path


if __name__ == "__main__":
    path = generate_code_map()
    print(f"Code map written to {path}")
    analysis_path = analyze_code_map(path)
    print(f"Analysis written to {analysis_path}")
