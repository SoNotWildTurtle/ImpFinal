from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "expansion" / "imp-coliseum-engine.py"
LOG = ROOT / "logs" / "imp-coliseum.json"

spec = importlib.util.spec_from_file_location("coliseum", MODULE)
coliseum = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coliseum)

print("Testing Coliseum Engine...")

LOG.write_text(json.dumps({
    "arenas": {},
    "players": {},
    "matches": [],
    "history": []
}))

arena = coliseum.register_arena("Aurora Pit", 16, tags=["ranked", "pve"], environment="ice")
assert arena["capacity"] == 16
assert "ranked" in arena["tags"]

player_one = coliseum.register_player("player-1", role="tank", base_rating=1050)
player_two = coliseum.register_player("player-2", role="mage")
assert player_one["rating"] == 1050
assert player_two["role"] == "mage"

first_match = coliseum.schedule_match("Aurora Pit", ["player-1"], mode="solo")
assert first_match["status"] == "scheduled"

second_match = coliseum.schedule_match("Aurora Pit", ["player-1", "player-2"], mode="duel")
result = coliseum.record_result(second_match["id"], "player-1", metadata={"duration": 120})
assert result["status"] == "completed"

leaderboard = coliseum.get_leaderboard()
assert leaderboard[0]["player"] == "player-1"
assert leaderboard[0]["rating"] > leaderboard[1]["rating"]

insights = coliseum.derive_mmo_insights()
assert "arena_utilization" in insights
assert any(entry["arena"] == "Aurora Pit" for entry in insights["arena_utilization"])
assert insights["player_focus"]["leaderboard"][0]["player"] == "player-1"

print("Coliseum Engine Test Passed!")
