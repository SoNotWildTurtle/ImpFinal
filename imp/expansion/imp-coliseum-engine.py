"""Coliseum coordination utilities for IMP.

This module manages arenas, players, and match scheduling for the
Coliseum feature set. Data is persisted to ``logs/imp-coliseum.json`` so
long-term metrics can drive MMO-scale planning.
"""
from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "logs" / "imp-coliseum.json"


def _blank_state() -> Dict[str, Any]:
    return {
        "arenas": {},
        "players": {},
        "matches": [],
        "history": [],
    }


def _load_state() -> Dict[str, Any]:
    state = _blank_state()
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            state["arenas"].update(data.get("arenas", {}))
            state["players"].update(data.get("players", {}))
            state["matches"] = list(data.get("matches", []))
            state["history"] = list(data.get("history", []))
    return state


def _save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def register_arena(name: str, capacity: int, *, tags: Iterable[str] | None = None,
                   environment: str | None = None) -> Dict[str, Any]:
    """Register or update an arena definition.

    Parameters
    ----------
    name:
        Arena identifier, e.g. "Aurora Pit".
    capacity:
        Maximum simultaneous competitors for the arena bracket.
    tags:
        Optional iterable describing supported modes ("ranked", "pve", etc.).
    environment:
        Optional biome descriptor used by MMO planners when selecting scenes.
    """
    state = _load_state()
    entry = state["arenas"].get(name, {})
    created = entry.get("created") or datetime.utcnow().isoformat()
    entry.update({
        "capacity": capacity,
        "tags": sorted(set(tags or [])),
        "environment": environment or entry.get("environment", "standard"),
        "created": created,
        "updated": datetime.utcnow().isoformat(),
    })
    state["arenas"][name] = entry
    _save_state(state)
    return entry


def register_player(player_id: str, *, role: str = "adventurer",
                    base_rating: int = 1000, guild: str | None = None) -> Dict[str, Any]:
    """Register a competitor for coliseum events."""
    state = _load_state()
    record = state["players"].get(player_id)
    if record is None:
        record = {
            "role": role,
            "rating": base_rating,
            "guild": guild,
            "matches": 0,
            "wins": 0,
            "losses": 0,
            "history": [],
            "joined": datetime.utcnow().isoformat(),
        }
    else:
        record.setdefault("rating", base_rating)
        record.setdefault("matches", 0)
        record.setdefault("wins", 0)
        record.setdefault("losses", 0)
        record.setdefault("history", [])
        if guild is not None:
            record["guild"] = guild
        if role:
            record["role"] = role
    record["updated"] = datetime.utcnow().isoformat()
    state["players"][player_id] = record
    _save_state(state)
    return record


def schedule_match(arena: str, players: List[str], *, mode: str,
                   scheduled_for: str | None = None,
                   metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Schedule a new match in the specified arena."""
    state = _load_state()
    if arena not in state["arenas"]:
        raise ValueError(f"Arena '{arena}' is not registered")
    missing = [player for player in players if player not in state["players"]]
    if missing:
        raise ValueError(f"Players not registered: {', '.join(missing)}")
    match_id = uuid.uuid4().hex
    entry = {
        "id": match_id,
        "arena": arena,
        "players": list(players),
        "mode": mode,
        "scheduled": scheduled_for or datetime.utcnow().isoformat(),
        "status": "scheduled",
        "metadata": metadata or {},
    }
    state["matches"].append(entry)
    _save_state(state)
    return entry


def _update_rating(record: Dict[str, Any], outcome: str) -> None:
    rating = int(record.get("rating", 1000))
    if outcome == "win":
        rating += 25
    else:
        rating = max(100, rating - 15)
    record["rating"] = rating


def record_result(match_id: str, winner: str,
                  metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Record the result for a scheduled match."""
    state = _load_state()
    for match in state["matches"]:
        if match["id"] == match_id:
            break
    else:
        raise ValueError(f"Match '{match_id}' not found")
    if winner not in match["players"]:
        raise ValueError(f"Winner '{winner}' did not participate in match {match_id}")
    timestamp = datetime.utcnow().isoformat()
    match["status"] = "completed"
    result = {
        "winner": winner,
        "completed": timestamp,
        "metadata": metadata or {},
    }
    match["result"] = result
    history_entry = {
        "match": match_id,
        "arena": match["arena"],
        "mode": match["mode"],
        "winner": winner,
        "players": list(match["players"]),
        "completed": timestamp,
    }
    state["history"].append(history_entry)
    for player_id in match["players"]:
        record = state["players"].get(player_id)
        if record is None:
            continue
        record["matches"] = int(record.get("matches", 0)) + 1
        if player_id == winner:
            record["wins"] = int(record.get("wins", 0)) + 1
            outcome = "win"
        else:
            record["losses"] = int(record.get("losses", 0)) + 1
            outcome = "loss"
        _update_rating(record, outcome)
        record.setdefault("history", []).append({
            "match": match_id,
            "outcome": outcome,
            "mode": match["mode"],
            "timestamp": timestamp,
        })
        record["updated"] = timestamp
    _save_state(state)
    return match


def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Return top competitors sorted by rating and wins."""
    state = _load_state()
    leaderboard = [
        {
            "player": player_id,
            "rating": data.get("rating", 1000),
            "wins": data.get("wins", 0),
            "losses": data.get("losses", 0),
            "role": data.get("role", "adventurer"),
        }
        for player_id, data in state["players"].items()
    ]
    leaderboard.sort(key=lambda entry: (entry["rating"], entry["wins"]), reverse=True)
    return leaderboard[:limit]


def derive_mmo_insights() -> Dict[str, Any]:
    """Aggregate trends so MMO planners can prioritise upgrades."""
    state = _load_state()
    arena_usage = Counter(match["arena"] for match in state["matches"])
    mode_usage = Counter(match["mode"] for match in state["matches"])
    player_activity = Counter()
    for match in state["matches"]:
        for player in match["players"]:
            player_activity[player] += 1
    role_wins = Counter()
    for entry in state["history"]:
        winner = entry.get("winner")
        role = state["players"].get(winner, {}).get("role", "adventurer")
        role_wins[role] += 1
    inactive = [pid for pid, data in state["players"].items() if data.get("matches", 0) == 0]
    recommendations: List[str] = []
    if arena_usage:
        busiest, matches = arena_usage.most_common(1)[0]
        capacity = state["arenas"].get(busiest, {}).get("capacity", 0)
        if capacity and matches >= capacity:
            recommendations.append(
                f"Arena '{busiest}' is saturated; open parallel brackets or expand capacity."
            )
    if inactive:
        recommendations.append(
            f"Design onboarding quests for {len(inactive)} inactive players to keep MMO retention high."
        )
    if role_wins:
        dominant_role, wins = role_wins.most_common(1)[0]
        recommendations.append(
            f"Balance check: '{dominant_role}' role has {wins} recent victories; ensure counters stay viable."
        )
    return {
        "arena_utilization": [
            {
                "arena": arena,
                "matches": count,
                "capacity": state["arenas"].get(arena, {}).get("capacity"),
            }
            for arena, count in arena_usage.most_common()
        ],
        "mode_trends": [
            {"mode": mode, "matches": count} for mode, count in mode_usage.most_common()
        ],
        "player_focus": {
            "active_players": len([pid for pid, c in player_activity.items() if c > 0]),
            "inactive_players": inactive,
            "leaderboard": get_leaderboard(5),
        },
        "role_success": [
            {"role": role, "wins": wins} for role, wins in role_wins.most_common()
        ],
        "mmo_recommendations": recommendations,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="IMP Coliseum Engine")
    parser.add_argument("--leaderboard", action="store_true", help="Display top competitors")
    parser.add_argument("--insights", action="store_true", help="Show MMO planning insights")
    parser.add_argument("--list-arenas", action="store_true", help="List registered arenas")
    args = parser.parse_args()

    if args.leaderboard:
        print(json.dumps(get_leaderboard(), indent=2))
    elif args.insights:
        print(json.dumps(derive_mmo_insights(), indent=2))
    elif args.list_arenas:
        state = _load_state()
        print(json.dumps(state["arenas"], indent=2))
    else:
        parser.print_help()
