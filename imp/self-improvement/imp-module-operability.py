"""Module operability audit driven by the planning methodology profile."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
PLAN_FILE = ROOT / "plan.json"
LOG_FILE = ROOT / "logs" / "imp-module-operability.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils = _load("imp_utils", ROOT / "core" / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json
goal_manager = _load("imp_goal_manager", ROOT / "core" / "imp-goal-manager.py")

DEFAULT_PROFILES = [
    {
        "name": "core",
        "required_paths": [
            "core/imp-execute.py",
            "core/imp-processing-manager.py",
            "core/imp-adaptive-planner.py",
        ],
        "required_tests": [
            "tests/test-execute-pipeline.py",
            "tests/test-processing-manager.py",
            "tests/test-adaptive-planner.py",
        ],
    },
    {
        "name": "security",
        "required_paths": [
            "security/imp-security-optimizer.py",
            "security/imp-session-guard.py",
            "security/imp-zero-trust-assessor.py",
        ],
        "required_tests": [
            "tests/test-security.py",
            "tests/test-session-guard.py",
            "tests/test-zero-trust-assessor.py",
        ],
    },
    {
        "name": "self-improvement",
        "required_paths": [
            "self-improvement/imp-self-healer.py",
            "self-improvement/imp-success-director.py",
            "self-improvement/imp-general-intelligence-review.py",
        ],
        "required_tests": [
            "tests/test-success-director.py",
            "tests/test-general-intelligence-review.py",
            "tests/test-roadmap-checker.py",
        ],
    },
    {
        "name": "expansion",
        "required_paths": [
            "expansion/imp-node-monitor.py",
            "expansion/imp-distributed-queue.py",
            "expansion/imp-cloud-orchestrator.py",
        ],
        "required_tests": [
            "tests/test-node-monitor.py",
            "tests/test-distributed-queue.py",
            "tests/test-cloud-orchestrator.py",
        ],
    },
]


def _timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _load_profiles() -> List[Dict[str, Any]]:
    data = read_json(PLAN_FILE, {})
    profiles = data.get("operability_profiles", []) if isinstance(data, dict) else []
    if isinstance(profiles, list) and profiles:
        return profiles
    return DEFAULT_PROFILES


def _load_plan() -> Dict[str, Any]:
    data = read_json(PLAN_FILE, {})
    return data if isinstance(data, dict) else {}


def _auto_goal_updates_enabled() -> bool:
    data = read_json(PLAN_FILE, {})
    if isinstance(data, dict):
        policy = data.get("operator_policy", {})
        if isinstance(policy, dict):
            return bool(policy.get("auto_generate_operability_goals", False))
    return False


def _import_check(path: Path) -> Dict[str, Any]:
    code = (
        "import importlib.util, sys; "
        f"spec=importlib.util.spec_from_file_location('mod', r'{path}'); "
        "m=importlib.util.module_from_spec(spec); "
        "sys.modules['mod']=m; "
        "spec.loader.exec_module(m)"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return {
            "ok": result.returncode == 0,
            "stderr": (result.stderr or "").strip()[:200],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stderr": "import timeout"}


def _goal_text_for_check(domain: str, check: Dict[str, Any]) -> str:
    kind = check.get("type")
    path = check.get("path")
    if kind == "source":
        return f"Restore methodology readiness by ensuring planning source exists for {domain}:{path}"
    if kind == "keyword":
        return f"Restore methodology readiness by aligning category keyword coverage for {domain}:{path}"
    if kind == "test":
        return f"Restore operability by adding/fixing test coverage for {domain}:{path}"
    if kind == "content":
        return f"Restore operability by aligning required file content for {domain}:{path}"
    if kind == "glob":
        return f"Restore operability by ensuring required assets exist for {domain}:{path}"
    return f"Restore operability by fixing module importability for {domain}:{path}"


def _methodology_checks(plan: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    sources = plan.get("sources", []) if isinstance(plan, dict) else []
    keywords = plan.get("category_keywords", {}) if isinstance(plan, dict) else {}
    priorities = plan.get("category_priority", {}) if isinstance(plan, dict) else {}

    source_texts: Dict[str, str] = {}
    for rel in sources if isinstance(sources, list) else []:
        rel_path = str(rel)
        path = ROOT / rel_path
        exists = path.exists()
        content = ""
        error = ""
        if exists:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                error = str(exc)[:200]
        else:
            error = "missing source file"
        source_texts[rel_path] = content
        checks.append(
            {
                "type": "source",
                "path": rel_path,
                "exists": exists,
                "ok": exists,
                "error": error,
            }
        )

    categories_covered = 0
    total_categories = 0
    for category, terms in keywords.items() if isinstance(keywords, dict) else []:
        terms_list = [str(term).lower() for term in terms] if isinstance(terms, list) else []
        if not terms_list:
            continue
        total_categories += 1
        combined = "\n".join(source_texts.values()).lower()
        matched = [term for term in terms_list if term and term in combined]
        required = str(priorities.get(category, "low")).lower() in {"high", "medium"}
        ok = bool(matched) if required else True
        if matched:
            categories_covered += 1
        checks.append(
            {
                "type": "keyword",
                "path": str(category),
                "required": required,
                "match_count": len(matched),
                "matched_keywords": matched[:10],
                "ok": ok,
                "error": "" if ok else "no category keywords found in methodology sources",
            }
        )

    metrics = {
        "sources_total": len(sources) if isinstance(sources, list) else 0,
        "categories_total": total_categories,
        "categories_covered": categories_covered,
        "category_coverage": round((categories_covered / total_categories) * 100.0, 2)
        if total_categories
        else 0.0,
    }
    return checks, metrics


def _append_operability_goals(domains: Dict[str, Any]) -> List[str]:
    goals = goal_manager.get_existing_goals()
    existing = {goal.get("goal", "") for goal in goals}
    added: List[str] = []

    for domain, data in domains.items():
        for check in data.get("checks", []):
            if check.get("ok"):
                continue
            text = _goal_text_for_check(domain, check)
            if text in existing:
                continue
            goals.append(
                {
                    "id": goal_manager._goal_id(),
                    "goal": text,
                    "term": "short-term",
                    "priority": "high",
                    "status": "pending",
                    "created_at": goal_manager._timestamp(),
                    "category": "operability",
                }
            )
            existing.add(text)
            added.append(text)

    if added:
        goal_manager.write_json(goal_manager.GOALS_FILE, goals)
    return added


def run_operability_audit(
    *,
    add_goals: bool | None = None,
    profiles: List[Dict[str, Any]] | None = None,
    include_methodology: bool = True,
) -> Dict[str, Any]:
    plan_data = _load_plan()
    profiles = profiles if profiles is not None else (
        plan_data.get("operability_profiles", []) if isinstance(plan_data.get("operability_profiles", []), list) else []
    )
    if not profiles:
        profiles = DEFAULT_PROFILES
    should_add_goals = _auto_goal_updates_enabled() if add_goals is None else add_goals
    domains: Dict[str, Any] = {}
    total_checks = 0
    passed_checks = 0

    for profile in profiles:
        name = profile.get("name", "unknown")
        required_paths = profile.get("required_paths", [])
        required_tests = profile.get("required_tests", [])
        required_content = profile.get("required_content", [])
        required_globs = profile.get("required_globs", [])
        domain_checks: List[Dict[str, Any]] = []

        for rel in required_paths:
            total_checks += 1
            path = ROOT / rel
            exists = path.exists()
            import_ok = False
            import_error = ""
            if exists and path.suffix == ".py":
                result = _import_check(path)
                import_ok = bool(result["ok"])
                import_error = result["stderr"]
            ok = exists and (import_ok if path.suffix == ".py" else True)
            if ok:
                passed_checks += 1
            domain_checks.append(
                {
                    "type": "module",
                    "path": rel,
                    "exists": exists,
                    "importable": import_ok if path.suffix == ".py" else None,
                    "ok": ok,
                    "error": import_error,
                }
            )

        for rel in required_tests:
            total_checks += 1
            path = ROOT / rel
            exists = path.exists()
            if exists:
                passed_checks += 1
            domain_checks.append(
                {
                    "type": "test",
                    "path": rel,
                    "exists": exists,
                    "ok": exists,
                }
            )

        for item in required_content:
            rel = item.get("path", "") if isinstance(item, dict) else ""
            patterns = item.get("contains", []) if isinstance(item, dict) else []
            mode = str(item.get("match", "all")).lower() if isinstance(item, dict) else "all"
            total_checks += 1
            path = ROOT / rel if rel else ROOT
            exists = path.exists()
            missing_patterns: List[str] = []
            content_ok = False
            error = ""
            if not exists:
                error = "missing file"
            elif not isinstance(patterns, list) or not patterns:
                error = "missing required content patterns"
            else:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    matched = [p for p in patterns if isinstance(p, str) and p in text]
                    if mode == "any":
                        content_ok = bool(matched)
                    else:
                        content_ok = len(matched) == len(patterns)
                    missing_patterns = [p for p in patterns if p not in matched]
                except Exception as exc:
                    error = str(exc)[:200]
            ok = exists and content_ok
            if ok:
                passed_checks += 1
            domain_checks.append(
                {
                    "type": "content",
                    "path": rel,
                    "exists": exists,
                    "patterns": patterns,
                    "match": mode,
                    "missing_patterns": missing_patterns,
                    "ok": ok,
                    "error": error,
                }
            )

        for pattern in required_globs:
            glob_pattern = str(pattern or "").strip()
            total_checks += 1
            if not glob_pattern:
                matches: List[Path] = []
                error = "missing glob pattern"
            else:
                matches = list(ROOT.glob(glob_pattern))
                error = ""
            ok = len(matches) > 0
            if ok:
                passed_checks += 1
            domain_checks.append(
                {
                    "type": "glob",
                    "path": glob_pattern,
                    "matches": [str(p.relative_to(ROOT)).replace("\\", "/") for p in matches[:10]],
                    "match_count": len(matches),
                    "ok": ok,
                    "error": error,
                }
            )

        domain_total = len(domain_checks)
        domain_passed = sum(1 for c in domain_checks if c["ok"])
        coverage = round((domain_passed / domain_total) * 100.0, 2) if domain_total else 0.0
        domains[name] = {
            "checks": domain_checks,
            "total": domain_total,
            "passed": domain_passed,
            "coverage": coverage,
        }

    methodology = {
        "sources_total": 0,
        "categories_total": 0,
        "categories_covered": 0,
        "category_coverage": 0.0,
    }
    if include_methodology:
        method_checks, methodology = _methodology_checks(plan_data)
        for check in method_checks:
            total_checks += 1
            if check.get("ok"):
                passed_checks += 1
        method_total = len(method_checks)
        method_passed = sum(1 for check in method_checks if check.get("ok"))
        domains["methodology-readiness"] = {
            "checks": method_checks,
            "total": method_total,
            "passed": method_passed,
            "coverage": round((method_passed / method_total) * 100.0, 2) if method_total else 0.0,
            "metrics": methodology,
        }

    summary = {
        "checked_at": _timestamp(),
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": max(0, total_checks - passed_checks),
        "coverage": round((passed_checks / total_checks) * 100.0, 2) if total_checks else 0.0,
        "domains": domains,
        "methodology": methodology,
        "goal_updates": [],
    }

    if should_add_goals:
        summary["goal_updates"] = _append_operability_goals(domains)

    history = read_json(LOG_FILE, [])
    if not isinstance(history, list):
        history = []
    history.append(summary)
    write_json(LOG_FILE, history)
    return summary


if __name__ == "__main__":
    result = run_operability_audit()
    print(
        f"Operability coverage: {result['coverage']}% "
        f"({result['passed_checks']}/{result['total_checks']})"
    )
