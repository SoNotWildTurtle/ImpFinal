from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "imp-adaptive-planner.py"
PLAN_FILE = ROOT / "logs" / "imp-strategy-plans.json"
CONTEXT_LOG = ROOT / "logs" / "imp-context-bundles.json"

# Ensure plan/context logs exist for test
PLAN_FILE.write_text("[]")
CONTEXT_LOG.write_text(
    '[{"created_at":"2026-02-26T00:00:00Z","sources":[{"source":"notes/self-evolution-plan.txt","exists":true,"matches":["Improve offline updates with GGUF models"]}]}]'
)

spec = importlib.util.spec_from_file_location("imp_adaptive_planner", MODULE_PATH)
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)

print("Testing adaptive planner...")
plan = planner.build_plan("Improve security and optimize performance.", mode="offline")
planner.save_plan(plan)

assert isinstance(plan, list) and len(plan) > 0
for item in plan:
    assert 0 <= item["weight"] <= 1
    assert "context_refs" in item
    assert "context_ref_count" in item
print("Adaptive planner test passed!")
