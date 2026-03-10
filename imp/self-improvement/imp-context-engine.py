"""Build an extended context bundle from methodology sources and recent logs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
IMP_DIR = ROOT / "imp"
LOG_DIR = IMP_DIR / "logs"
PLAN_FILE = IMP_DIR / "plan.json"
CONTEXT_LOG = LOG_DIR / "imp-context-bundles.json"


def _load(name: str, path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils = _load("imp_utils", IMP_DIR / "core" / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json


def _timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _source_path(raw: str) -> Path:
    return (IMP_DIR / raw).resolve()


def _extract_matches(text: str, keywords: List[str], limit: int) -> List[str]:
    lowered_keywords = [k.lower() for k in keywords if isinstance(k, str) and k.strip()]
    if not lowered_keywords:
        return []
    matches: List[str] = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        low = cleaned.lower()
        if any(key in low for key in lowered_keywords):
            matches.append(cleaned[:240])
            if len(matches) >= limit:
                break
    return matches


def _recent_log_entry(path: Path) -> Dict[str, Any]:
    data = read_json(path, [])
    if isinstance(data, list):
        last = data[-1] if data else None
        return {"entries": len(data), "latest": last}
    if isinstance(data, dict):
        return {"entries": 1, "latest": data}
    return {"entries": 0, "latest": None}


def build_context_bundle(limit_per_source: int = 5, add_recent_logs: bool = True) -> Dict[str, Any]:
    plan = read_json(PLAN_FILE, {})
    sources = plan.get("sources", []) if isinstance(plan, dict) else []
    category_keywords = plan.get("category_keywords", {}) if isinstance(plan, dict) else {}
    keywords: List[str] = []
    if isinstance(category_keywords, dict):
        for values in category_keywords.values():
            if isinstance(values, list):
                keywords.extend(str(v) for v in values if isinstance(v, str))

    source_summaries: List[Dict[str, Any]] = []
    for source in sources:
        rel = str(source)
        path = _source_path(rel)
        exists = path.exists()
        summary: Dict[str, Any] = {"source": rel, "exists": exists}
        if exists and path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            summary["size_bytes"] = path.stat().st_size
            summary["line_count"] = len(text.splitlines())
            summary["matches"] = _extract_matches(text[:40000], keywords, max(1, limit_per_source))
        else:
            summary["size_bytes"] = 0
            summary["line_count"] = 0
            summary["matches"] = []
        source_summaries.append(summary)

    bundle: Dict[str, Any] = {
        "created_at": _timestamp(),
        "sources": source_summaries,
        "source_count": len(source_summaries),
        "missing_sources": [s["source"] for s in source_summaries if not s["exists"]],
    }

    if add_recent_logs:
        bundle["recent_logs"] = {
            "general_review": _recent_log_entry(LOG_DIR / "imp-general-intelligence-review.json"),
            "success_plan": _recent_log_entry(LOG_DIR / "imp-success-plan.json"),
            "operability": _recent_log_entry(LOG_DIR / "imp-module-operability.json"),
        }

    history = read_json(CONTEXT_LOG, [])
    if not isinstance(history, list):
        history = []
    history.append(bundle)
    write_json(CONTEXT_LOG, history)
    return bundle


if __name__ == "__main__":
    result = build_context_bundle()
    print(
        f"Context bundle created with {result['source_count']} sources "
        f"({len(result['missing_sources'])} missing)."
    )
