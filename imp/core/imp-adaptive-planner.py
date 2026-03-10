"""Adaptive planner with optional context-aware grounding.

If an OpenAI API key is available the planner can request ChatGPT to break down
a directive into subgoals. Offline mode falls back to heuristic splitting.
When context bundles exist, each subgoal can include matching context snippets.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Dict, List

import importlib.util

spec_utils = importlib.util.spec_from_file_location(
    "imp_utils", Path(__file__).resolve().parent / "imp_utils.py"
)
imp_utils = importlib.util.module_from_spec(spec_utils)
spec_utils.loader.exec_module(imp_utils)

try:  # optional dependency for online planning
    import openai
except Exception:  # pragma: no cover - networkless environments
    openai = None

ROOT = Path(__file__).resolve().parents[1]
PLAN_FILE = ROOT / "logs" / "imp-strategy-plans.json"
CONTEXT_LOG = ROOT / "logs" / "imp-context-bundles.json"

# track last request time for crude rate limiting
OPENAI_LAST_REQUEST: Dict[str, float] = {}
OPENAI_RPM: Dict[str, int] = {
    "gpt-3.5-turbo": 60,
    "gpt-4": 40,
}


def decide_mode() -> str:
    """Return 'online' if the OpenAI key is set, otherwise 'offline'."""
    if openai is not None and os.getenv("OPENAI_API_KEY"):
        return "online"
    return "offline"


def _throttle(model: str) -> None:
    """Sleep to respect OpenAI rate limits divided by four."""
    rpm = OPENAI_RPM.get(model, 60)
    interval = 60 / (rpm / 4)
    last = OPENAI_LAST_REQUEST.get(model, 0)
    elapsed = time.time() - last
    if elapsed < interval:
        time.sleep(interval - elapsed)
    OPENAI_LAST_REQUEST[model] = time.time()


def _split_directive(directive: str) -> List[str]:
    """Split a high-level directive into rough subgoals."""
    parts = re.split(r"[.;]| and | then ", directive)
    return [p.strip() for p in parts if p.strip()]


def _weigh_goal(goal: str) -> float:
    """Estimate a weight for a subgoal based on length heuristics."""
    length = len(goal.split())
    benefit = min(length / 5.0, 1.0)
    feasibility = max(0.1, 1.0 - length / 20.0)
    return round((benefit + feasibility) / 2.0, 2)


def _context_snippets() -> List[str]:
    """Return recent context snippets from context bundle history."""
    history = imp_utils.read_json(CONTEXT_LOG, [])
    if not isinstance(history, list) or not history:
        return []
    latest = history[-1] if isinstance(history[-1], dict) else {}
    snippets: List[str] = []
    for src in latest.get("sources", []) if isinstance(latest, dict) else []:
        if not isinstance(src, dict):
            continue
        for match in src.get("matches", []):
            if isinstance(match, str) and match.strip():
                snippets.append(match.strip())
                if len(snippets) >= 40:
                    return snippets
    return snippets


def _goal_context_refs(goal: str, snippets: List[str], limit: int = 2) -> List[str]:
    """Select snippets that overlap with the goal text."""
    if not snippets:
        return []
    tokens = {t for t in re.split(r"[^a-zA-Z0-9]+", goal.lower()) if len(t) >= 4}
    if not tokens:
        return []
    refs: List[str] = []
    for snippet in snippets:
        lowered = snippet.lower()
        if any(token in lowered for token in tokens):
            refs.append(snippet[:240])
            if len(refs) >= limit:
                break
    return refs


def build_plan(directive: str, mode: str = "auto", include_context: bool = True) -> List[Dict[str, object]]:
    """Return weighted subgoals derived from a directive.

    In online mode the directive is sent to ChatGPT which returns a numbered
    list of subgoals. Offline mode falls back to heuristic splitting.
    """
    if mode == "auto":
        mode = decide_mode()

    subgoals: List[str] = []
    if mode == "online" and openai is not None and os.getenv("OPENAI_API_KEY"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        try:
            _throttle("gpt-3.5-turbo")
            prompt = (
                "Break the following directive into a short numbered list of "
                "actionable subgoals:\n" + directive
            )
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp["choices"][0]["message"]["content"]
            lines = [re.sub(r"^[0-9]+[.)]\s*", "", l).strip() for l in text.splitlines()]
            subgoals = [l for l in lines if l]
        except Exception:
            subgoals = []

    if not subgoals:
        subgoals = _split_directive(directive)

    snippets = _context_snippets() if include_context else []
    plan: List[Dict[str, object]] = []
    for sg in subgoals:
        item: Dict[str, object] = {"goal": sg, "weight": _weigh_goal(sg)}
        if include_context:
            refs = _goal_context_refs(sg, snippets)
            item["context_refs"] = refs
            item["context_ref_count"] = len(refs)
        plan.append(item)
    return plan


def save_plan(plan: List[Dict[str, object]]) -> None:
    imp_utils.write_json(PLAN_FILE, plan)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="IMP Adaptive Planner")
    parser.add_argument(
        "--mode",
        choices=["online", "offline", "auto"],
        default="auto",
        help="Choose online, offline, or auto planning mode",
    )
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Disable context snippet grounding in generated subgoals.",
    )
    args = parser.parse_args()

    directive = input("Enter high-level directive: ")
    plan = build_plan(directive, args.mode, include_context=not args.no_context)
    save_plan(plan)
    for item in plan:
        print(f"{item['goal']} (weight={item['weight']})")
