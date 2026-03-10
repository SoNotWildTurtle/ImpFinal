import importlib.util

import json

from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]

MODULE_PATH = ROOT / "core" / "imp-autonomy-controller.py"



spec = importlib.util.spec_from_file_location("imp_autonomy_controller", MODULE_PATH)

autonomy = importlib.util.module_from_spec(spec)

spec.loader.exec_module(autonomy)



AutonomyController = autonomy.AutonomyController

BUG_LOG = autonomy.BUG_LOG

HEAL_LOG = autonomy.HEAL_LOG



print("Testing Autonomy Controller...")





def _write_json(path: Path, payload) -> None:

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(json.dumps(payload, indent=2))





def test_autonomy_controller_cycle(tmp_path):

    bug_backup = BUG_LOG.read_text() if BUG_LOG.exists() else "[]"

    heal_backup = HEAL_LOG.read_text() if HEAL_LOG.exists() else "[]"



    try:

        _write_json(BUG_LOG, [])

        _write_json(HEAL_LOG, [])



        log_path = tmp_path / "autonomy-log.json"
        action_memory_path = tmp_path / "autonomy-action-memory.json"



        commands = []



        def fake_runner(command, timeout=0.0):

            commands.append((tuple(command), timeout))

            if command[:2] == ["bash", "tests/run-all-tests.sh"]:

                return {

                    "command": command,

                    "success": True,

                    "stdout": "All good",

                    "stderr": "",

                    "code": 0,

                    "duration": 12.5,

                }

            return {

                "command": command,

                "success": True,

                "stdout": "",

                "stderr": "",

                "code": 0,

                "duration": 0.0,

            }



        def fake_code_map():

            path = tmp_path / "code-map.json"

            _write_json(path, {"ok": True})

            return path



        def fake_analysis(path=None):

            analysis = tmp_path / "analysis.json"

            _write_json(analysis, {"analysis": True})

            return analysis



        def fake_bug_scan(**kwargs):

            _write_json(BUG_LOG, [{"file": "imp/example.py", "error": "E"}])



        heal_calls = []



        def fake_self_heal(**kwargs):

            heal_calls.append(kwargs)

            _write_json(HEAL_LOG, [{"tests_passed": True, "lint_issues": []}])

            return [{"file": "imp/example.py"}]



        goal_calls = []



        def fake_goal_update(**kwargs):

            goal_calls.append(kwargs)

            return ["Address TODOs in imp/example.py"]



        plan_calls = []



        def fake_success_plan(**kwargs):

            plan_calls.append(kwargs)

            return {

                "plan": {

                    "actions": [

                        {

                            "goal": "Low context task",

                            "category": "self-management",

                            "priority": "medium",

                            "term": "short-term",

                            "context_ref_count": 0,

                        },

                        {

                            "goal": "Contextual high-value task",

                            "category": "self-management",

                            "priority": "medium",

                            "term": "short-term",

                            "context_ref_count": 3,

                        }

                    ]

                },

                "goals_added": ["Address TODOs in imp/example.py"],

            }



        handlers = {

            "self-management": lambda action: {"ack": action.get("goal")},

        }



        controller = AutonomyController(

            runner=fake_runner,

            log_path=log_path,
            action_memory_path=action_memory_path,

            cooldown_seconds=0,

            ensure_logs_fn=lambda: None,

            code_map_fn=fake_code_map,

            code_analysis_fn=fake_analysis,

            bug_scan_fn=fake_bug_scan,

            self_healer_fn=fake_self_heal,

            goal_update_fn=fake_goal_update,

            success_plan_fn=fake_success_plan,

            action_handlers=handlers,

        )



        controller.cooldown = 5

        controller.govern()

        log_data = json.loads(log_path.read_text())

        assert len(log_data) == 1

        entry = log_data[0]

        assert entry["status"] == "completed"

        assert entry["bug_scan"]["issues"] == 1

        assert entry["self_heal"]["mismatches"] == 1

        assert entry["self_heal"]["repair_attempted"] is True

        assert entry["self_heal"]["tests_passed"] is True

        assert entry["tests"]["success"] is True

        assert entry["tests"]["duration"] == 12.5

        assert entry["git"]["clean"] is True

        assert entry["summary"]["goal_updates"]["count"] == 1

        assert entry["summary"]["success_plan"]["actions"] == 2

        assert entry["summary"]["control_actions"][0]["outcome"]["ack"] == "Contextual high-value task"

        assert entry["summary"]["control_actions"][0]["context_ref_count"] == 3

        assert entry["summary"]["control_actions"][0]["context_score"] >= 3

        assert entry["summary"]["control_actions"][1]["outcome"]["ack"] == "Low context task"

        assert heal_calls[0]["apply"] is False

        assert heal_calls[1]["apply"] is True

        assert goal_calls and plan_calls

        assert any(cmd[0][0] == "bash" for cmd in commands)



        controller.govern()

        log_data = json.loads(log_path.read_text())

        assert len(log_data) == 2

        assert log_data[-1]["status"] == "skipped"

        assert log_data[-1].get("forced") is False



        controller.govern(force=True)

        log_data = json.loads(log_path.read_text())

        assert len(log_data) == 3

        assert log_data[-1]["status"] == "completed"

        assert log_data[-1].get("forced") is True

    finally:

        _write_json(BUG_LOG, json.loads(bug_backup or "[]"))

        _write_json(HEAL_LOG, json.loads(heal_backup or "[]"))


def test_autonomy_action_memory_feedback(tmp_path):
    bug_backup = BUG_LOG.read_text() if BUG_LOG.exists() else "[]"
    heal_backup = HEAL_LOG.read_text() if HEAL_LOG.exists() else "[]"
    try:
        _write_json(BUG_LOG, [])
        _write_json(HEAL_LOG, [])

        log_path = tmp_path / "autonomy-log-memory.json"
        memory_path = tmp_path / "autonomy-action-memory.json"

        def fake_runner(command, timeout=0.0):
            if command[:2] == ["bash", "tests/run-all-tests.sh"]:
                return {"command": command, "success": True, "stdout": "", "stderr": "", "code": 0, "duration": 1.0}
            return {"command": command, "success": True, "stdout": "", "stderr": "", "code": 0, "duration": 0.0}

        def fake_success_plan(**kwargs):
            return {
                "plan": {
                    "actions": [
                        {
                            "goal": "Historically unstable contextual task",
                            "category": "self-management",
                            "priority": "medium",
                            "term": "short-term",
                            "context_ref_count": 3,
                        },
                        {
                            "goal": "Historically stable low-context task",
                            "category": "self-management",
                            "priority": "medium",
                            "term": "short-term",
                            "context_ref_count": 0,
                        },
                    ]
                },
                "goals_added": [],
            }

        def flaky_handler(action):
            if action.get("goal") == "Historically unstable contextual task":
                return {"error": "simulated"}
            return {"ack": action.get("goal")}

        controller = AutonomyController(
            runner=fake_runner,
            log_path=log_path,
            action_memory_path=memory_path,
            cooldown_seconds=0,
            ensure_logs_fn=lambda: None,
            code_map_fn=lambda: tmp_path / "code-map.json",
            code_analysis_fn=lambda path=None: tmp_path / "analysis.json",
            bug_scan_fn=lambda **kwargs: _write_json(BUG_LOG, []),
            self_healer_fn=lambda **kwargs: [],
            goal_update_fn=lambda **kwargs: [],
            success_plan_fn=fake_success_plan,
            action_handlers={"self-management": flaky_handler},
        )

        controller.govern(force=True)
        first_entry = json.loads(log_path.read_text())[-1]
        assert first_entry["summary"]["control_actions"][0]["goal"] == "Historically unstable contextual task"

        controller.govern(force=True)
        second_entry = json.loads(log_path.read_text())[-1]
        assert second_entry["summary"]["control_actions"][0]["goal"] == "Historically stable low-context task"

        memory = json.loads(memory_path.read_text())
        assert any(not item.get("success") for item in memory)
        assert any(item.get("success") for item in memory)
    finally:
        _write_json(BUG_LOG, json.loads(bug_backup or "[]"))
        _write_json(HEAL_LOG, json.loads(heal_backup or "[]"))

