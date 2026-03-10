"""Central coordinator that lets IMP govern its own lifecycle."""



from __future__ import annotations



import importlib.util

import json

import subprocess

import time

from datetime import datetime, timedelta, timezone

from pathlib import Path

from typing import Any, Callable, Dict, Iterable, List, Optional



CORE_DIR = Path(__file__).resolve().parent

ROOT = CORE_DIR.parent





def _load(name: str, path: Path):

    spec = importlib.util.spec_from_file_location(name, path)

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module





imp_utils = _load("imp_utils", CORE_DIR / "imp_utils.py")

read_json = imp_utils.read_json

write_json = imp_utils.write_json

load_module = imp_utils.load_module



log_manager = load_module("imp_log_manager", ROOT / "logs" / "imp-log-manager.py")

code_map_module = load_module("imp_code_map", ROOT / "self-improvement" / "imp-code-map.py")

bug_hunter_module = load_module("imp_bug_hunter", ROOT / "self-improvement" / "imp-bug-hunter.py")

self_healer_module = load_module("imp_self_healer", ROOT / "self-improvement" / "imp-self-healer.py")

goal_manager_module = load_module("imp_goal_manager", CORE_DIR / "imp-goal-manager.py")

success_director_module = load_module(

    "imp_success_director", ROOT / "self-improvement" / "imp-success-director.py"

)



try:

    learning_memory_module = load_module(

        "imp_learning_memory", CORE_DIR / "imp-learning-memory.py"

    )

except Exception:  # pragma: no cover - optional dependency

    learning_memory_module = None



try:

    roadmap_checker_module = load_module(

        "imp_roadmap_checker", ROOT / "self-improvement" / "imp-roadmap-checker.py"

    )

except Exception:  # pragma: no cover - optional dependency

    roadmap_checker_module = None



try:

    network_tester_module = load_module(

        "imp_3d_network_tester", ROOT / "self-improvement" / "imp-3d-network-tester.py"

    )

except Exception:  # pragma: no cover - optional dependency

    network_tester_module = None



ensure_logs = getattr(log_manager, "ensure_logs")



default_code_map = getattr(code_map_module, "generate_code_map")

default_analysis = getattr(code_map_module, "analyze_code_map")

default_bug_scan = getattr(bug_hunter_module, "scan_repository")

default_self_heal = getattr(self_healer_module, "verify_and_heal")

default_goal_update = getattr(goal_manager_module, "add_goals_from_code_map")

default_success_plan = getattr(success_director_module, "build_success_plan")



BUG_LOG = ROOT / "logs" / "imp-bug-report.json"

HEAL_LOG = ROOT / "logs" / "imp-self-heal-log.json"

AUTONOMY_LOG = ROOT / "logs" / "imp-autonomy-log.json"
AUTONOMY_ACTION_MEMORY_LOG = ROOT / "logs" / "imp-autonomy-action-memory.json"





class AutonomyController:

    """Orchestrate high-level self-governance loops for IMP."""



    LOG_LIMIT = 200



    def __init__(

        self,

        *,

        runner: Optional[Callable[[List[str], float], Dict[str, Any]]] = None,

        log_path: Optional[Path] = None,

        action_memory_path: Optional[Path] = None,

        cooldown_seconds: int = 1800,

        ensure_logs_fn: Callable[[], None] = ensure_logs,

        code_map_fn: Callable[[], Path] = default_code_map,

        code_analysis_fn: Callable[[Optional[Path]], Path] = default_analysis,

        bug_scan_fn: Callable[..., Any] = default_bug_scan,

        self_healer_fn: Callable[..., Iterable] = default_self_heal,

        goal_update_fn: Callable[..., List[str]] = default_goal_update,

        success_plan_fn: Callable[..., Dict[str, Any]] = default_success_plan,

        action_handlers: Optional[Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]] = None,

    ) -> None:

        self.runner = runner or self._default_runner

        self.log_path = log_path or AUTONOMY_LOG

        self.action_memory_path = action_memory_path or AUTONOMY_ACTION_MEMORY_LOG

        self.cooldown = max(0, int(cooldown_seconds))

        self.ensure_logs_fn = ensure_logs_fn

        self.code_map_fn = code_map_fn

        self.code_analysis_fn = code_analysis_fn

        self.bug_scan_fn = bug_scan_fn

        self.self_healer_fn = self_healer_fn

        self.goal_update_fn = goal_update_fn

        self.success_plan_fn = success_plan_fn

        self.action_handlers = action_handlers or self._default_action_handlers()

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.log_path.exists():

            write_json(self.log_path, [])

        self.action_memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.action_memory_path.exists():
            write_json(self.action_memory_path, [])



    # ------------------------------------------------------------------

    # Internal helpers

    # ------------------------------------------------------------------

    @staticmethod

    def _now() -> str:

        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")



    @staticmethod

    def _parse_timestamp(value: str) -> Optional[datetime]:

        try:

            if value.endswith("Z"):

                value = value[:-1] + "+00:00"

            return datetime.fromisoformat(value)

        except ValueError:

            return None



    def _default_runner(self, command: List[str], timeout: float = 900.0) -> Dict[str, Any]:

        start = time.time()

        try:

            result = subprocess.run(

                command,

                capture_output=True,

                text=True,

                timeout=timeout,

                cwd=ROOT,

            )

        except subprocess.TimeoutExpired as exc:  # pragma: no cover - timeout rarely triggered in tests

            return {

                "command": command,

                "success": False,

                "stdout": exc.stdout or "",

                "stderr": exc.stderr or "timeout",

                "code": None,

                "duration": time.time() - start,

            }

        return {

            "command": command,

            "success": result.returncode == 0,

            "stdout": result.stdout,

            "stderr": result.stderr,

            "code": result.returncode,

            "duration": time.time() - start,

        }



    def _load_log(self) -> List[Dict[str, Any]]:

        return list(read_json(self.log_path, []))



    def _record(self, entry: Dict[str, Any]) -> None:

        log = self._load_log()

        log.append(entry)

        if len(log) > self.LOG_LIMIT:

            log = log[-self.LOG_LIMIT :]

        write_json(self.log_path, log)



    def _should_run(self, force: bool = False) -> bool:

        if force:

            return True

        if self.cooldown <= 0:

            return True

        log = self._load_log()

        if not log:

            return True

        last = log[-1]

        ts = last.get("timestamp")

        if not isinstance(ts, str):

            return True

        parsed = self._parse_timestamp(ts)

        if parsed is None:

            return True

        elapsed = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)

        return elapsed >= timedelta(seconds=self.cooldown)



    def _git_status(self) -> Dict[str, Any]:

        result = self.runner(["git", "status", "--porcelain"], timeout=120.0)

        stdout = result.get("stdout") or ""

        changes = [line for line in stdout.splitlines() if line.strip()]

        info = {"clean": not changes, "changes": len(changes)}

        if not result.get("success", False):

            info["error"] = (result.get("stderr") or "").strip()

        return info



    def _default_action_handlers(self) -> Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]:

        handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}



        def _self_management(_: Dict[str, Any]) -> Dict[str, Any]:

            goals = goal_manager_module.get_existing_goals()

            status_counts: Dict[str, int] = {}

            for goal in goals:

                status = str(goal.get("status", "pending")).lower()

                status_counts[status] = status_counts.get(status, 0) + 1

            return {

                "total_goals": len(goals),

                "status_counts": status_counts,

            }



        handlers["self-management"] = _self_management



        if learning_memory_module is not None:



            def _reflection(_: Dict[str, Any]) -> Dict[str, Any]:

                file_path = getattr(learning_memory_module, "LEARNING_FILE")

                before = learning_memory_module.read_json(file_path, [])

                learning_memory_module.store_learnings()

                after = learning_memory_module.read_json(file_path, [])

                delta = max(0, len(after) - len(before))

                new_entries = after[-delta:] if delta else []

                categories = (

                    learning_memory_module.summarise_categories(new_entries)

                    if new_entries

                    else {}

                )

                return {"new_entries": delta, "categories": categories}



            handlers["reflection"] = _reflection



        if roadmap_checker_module is not None:



            def _roadmap(_: Dict[str, Any]) -> Dict[str, Any]:

                progress = roadmap_checker_module.check_progress()

                summary = progress.get("summary", {}) if isinstance(progress, dict) else {}

                return {

                    "coverage": summary.get("coverage"),

                    "modules_missing": summary.get("modules_missing"),

                    "checked_at": summary.get("checked_at"),

                }



            handlers["roadmap"] = _roadmap



        if network_tester_module is not None:



            def _neural_evolution(_: Dict[str, Any]) -> Dict[str, Any]:

                base = network_tester_module.load_or_create_network()

                candidate = network_tester_module.create_candidate(base)

                diff = network_tester_module.analyzer_module.compare_3d_networks(

                    base, candidate

                )

                try:

                    candidate.save(network_tester_module.CANDIDATE_FILE)

                except Exception:

                    pass

                return {

                    "neuron_delta": diff.get("neuron_count_diff"),

                    "connection_delta": diff.get("connection_count_diff"),

                    "new_types": diff.get("new_types", []),

                }



            handlers["neural-evolution"] = _neural_evolution



        return handlers



    def _execute_plan_actions(

        self, actions: Iterable[Dict[str, Any]]

    ) -> List[Dict[str, Any]]:

        results: List[Dict[str, Any]] = []

        for action in actions:

            category = str(action.get("category") or "").lower()

            handler = self.action_handlers.get(category)

            if handler is None:

                continue

            try:

                outcome = handler(action)

            except Exception as exc:  # pragma: no cover - defensive

                outcome = {"error": repr(exc)}

            self._record_action_memory(action, outcome if isinstance(outcome, dict) else {"error": "invalid"})

            results.append(

                {

                    "goal": action.get("goal"),

                    "category": category,
                    "context_score": self._context_score(action),
                    "context_ref_count": self._context_ref_count(action),
                    "memory_bonus": self._action_memory_bonus(action),
                    "outcome": outcome,

                }

            )

        return results

    @staticmethod
    def _priority_rank(priority: Any) -> int:
        mapping = {"high": 0, "medium": 1, "low": 2}
        return mapping.get(str(priority or "").lower(), 3)

    @staticmethod
    def _context_ref_count(action: Dict[str, Any]) -> int:
        direct = action.get("context_ref_count")
        if isinstance(direct, int):
            return max(0, direct)
        refs = action.get("context_refs")
        if isinstance(refs, list):
            return len([r for r in refs if isinstance(r, str) and r.strip()])
        return 0

    def _context_score(self, action: Dict[str, Any]) -> int:
        score = self._context_ref_count(action)
        reason = str(action.get("reason") or "").lower()
        if "offline" in reason or "operability" in reason:
            score += 1
        return score

    def _load_action_memory(self) -> List[Dict[str, Any]]:
        data = read_json(self.action_memory_path, [])
        if isinstance(data, list):
            return data
        return []

    @staticmethod
    def _action_memory_key(action: Dict[str, Any]) -> str:
        goal = str(action.get("goal") or "").strip()
        category = str(action.get("category") or "").strip().lower()
        return f"{category}::{goal}"

    def _action_memory_bonus(self, action: Dict[str, Any]) -> float:
        key = self._action_memory_key(action)
        if not key.endswith("::"):
            memory = self._load_action_memory()
            score = 0.0
            for item in memory[-200:]:
                if not isinstance(item, dict):
                    continue
                if item.get("key") != key:
                    continue
                score += 1.0 if item.get("success") else -1.0
            return max(-3.0, min(3.0, score))
        return 0.0

    def _record_action_memory(self, action: Dict[str, Any], outcome: Dict[str, Any]) -> None:
        memory = self._load_action_memory()
        item = {
            "timestamp": self._now(),
            "key": self._action_memory_key(action),
            "goal": action.get("goal"),
            "category": action.get("category"),
            "success": not bool(outcome.get("error")) if isinstance(outcome, dict) else False,
            "context_score": self._context_score(action),
            "context_ref_count": self._context_ref_count(action),
        }
        memory.append(item)
        if len(memory) > 1000:
            memory = memory[-1000:]
        write_json(self.action_memory_path, memory)

    def _prioritize_actions(self, actions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: Dict[str, Dict[str, Any]] = {}
        for action in actions:
            goal = str(action.get("goal") or "").strip()
            if not goal:
                continue
            existing = deduped.get(goal)
            if existing is None or self._context_score(action) > self._context_score(existing):
                deduped[goal] = action
        return sorted(
            deduped.values(),
            key=lambda action: (
                0 if str(action.get("category", "")).lower() == "operability" else 1,
                self._priority_rank(action.get("priority")),
                -self._action_memory_bonus(action),
                -self._context_score(action),
                0 if str(action.get("term", "")).lower() == "short-term" else 1,
            ),
        )
    def _run_bug_scan(self, summary: Dict[str, Any]) -> Dict[str, Any]:

        try:

            self.bug_scan_fn(batch_size=40, pause=0.0)

        except TypeError:

            self.bug_scan_fn()

        except Exception as exc:  # pragma: no cover - defensive logging

            summary["bug_scan_error"] = repr(exc)

            return {"issues": None}

        issues = read_json(BUG_LOG, [])

        return {"issues": len(issues) if isinstance(issues, list) else None}



    def _run_self_heal(self, summary: Dict[str, Any]) -> Dict[str, Any]:

        mismatches: Optional[Iterable[Any]] = None

        try:

            mismatches = self.self_healer_fn(

                apply=False,

                use_chatgpt=False,

                mode="auto",

                mint=False,

            )

        except TypeError:

            mismatches = self.self_healer_fn()

        except Exception as exc:  # pragma: no cover - defensive logging

            summary["self_heal_error"] = repr(exc)

            return {"mismatches": None}



        mismatch_count: Optional[int]

        mismatch_list: List[Any] | None = None

        if mismatches is None:

            mismatch_count = None

        elif isinstance(mismatches, Iterable) and not isinstance(mismatches, (str, bytes)):

            mismatch_list = list(mismatches)

            mismatch_count = len(mismatch_list)

        else:

            mismatch_count = None



        heal_info: Dict[str, Any] = {"mismatches": mismatch_count, "repair_attempted": False}

        try:

            log = read_json(HEAL_LOG, [])

            if isinstance(log, list) and log:

                last = log[-1]

                if isinstance(last, dict):

                    heal_info["tests_passed"] = last.get("tests_passed")

                    lint = last.get("lint_issues")

                    if isinstance(lint, list):

                        heal_info["lint_issues"] = len(lint)

                    else:

                        heal_info["lint_issues"] = lint

        except Exception:  # pragma: no cover - best effort read

            pass



        if mismatch_count and mismatch_count > 0:

            try:

                follow_up = self.self_healer_fn(

                    apply=True,

                    use_chatgpt=False,

                    mode="auto",

                    mint=False,

                )

                heal_info["repair_attempted"] = True

                if isinstance(follow_up, Iterable) and not isinstance(follow_up, (str, bytes)):

                    heal_info["repair_mismatches"] = len(list(follow_up))

                else:

                    heal_info["repair_mismatches"] = None

            except TypeError:

                self.self_healer_fn()

                heal_info["repair_attempted"] = True

            except Exception as exc:  # pragma: no cover - defensive logging

                summary["self_heal_apply_error"] = repr(exc)

        elif mismatch_list is not None:

            heal_info["repair_mismatches"] = len(mismatch_list)

        return heal_info



    def _run_tests(self) -> Dict[str, Any]:

        """Execute the integration test suite and capture a compact report."""



        result = self.runner(["bash", "tests/run-all-tests.sh"], timeout=3600.0)

        info = {

            "success": bool(result.get("success")),

            "code": result.get("code"),

            "duration": result.get("duration"),

        }

        stderr = result.get("stderr") or ""

        if not info["success"] and stderr:

            lines = [line.strip() for line in stderr.splitlines() if line.strip()]

            if lines:

                info["error"] = lines[0][:200]

        return info



    # ------------------------------------------------------------------

    # Public API

    # ------------------------------------------------------------------

    def govern(self, force: bool = False) -> None:

        """Execute a governance cycle if the cooldown has expired."""



        if not self._should_run(force=force):

            self._record(

                {

                    "timestamp": self._now(),

                    "status": "skipped",

                    "reason": "cooldown_active",

                    "forced": False,

                }

            )

            return



        summary: Dict[str, Any] = {}

        try:

            self.ensure_logs_fn()

        except Exception as exc:  # pragma: no cover - defensive logging

            summary["ensure_logs_error"] = repr(exc)



        code_map_path: Optional[Path] = None

        try:

            code_map_path = self.code_map_fn()

            summary["code_map"] = str(code_map_path)

        except Exception as exc:

            summary["code_map_error"] = repr(exc)



        try:

            analysis_path = self.code_analysis_fn(code_map_path)  # type: ignore[arg-type]

            summary["analysis"] = str(analysis_path)

        except Exception as exc:

            summary["analysis_error"] = repr(exc)



        try:

            updates = self.goal_update_fn(

                term="long-term",

                priority="medium",

                category="code-quality",

            )

            if updates:

                summary["goal_updates"] = {

                    "count": len(updates),

                    "samples": updates[:3],

                }

            else:

                summary["goal_updates"] = {"count": 0}

        except Exception as exc:

            summary["goal_update_error"] = repr(exc)



        try:

            plan_result = self.success_plan_fn(add_goals=True)

            plan_data = plan_result.get("plan", {}) if isinstance(plan_result, dict) else {}

            actions = plan_data.get("actions", []) if isinstance(plan_data, dict) else []
            actions = self._prioritize_actions(actions)

            goals_added = plan_result.get("goals_added", []) if isinstance(plan_result, dict) else []

            summary["success_plan"] = {

                "actions": len(actions),

                "goals_added": len(goals_added),

            }

            if actions:

                first_action = actions[0]

                if isinstance(first_action, dict):

                    summary["success_plan"]["sample"] = {

                        "goal": first_action.get("goal"),

                        "priority": first_action.get("priority"),

                        "term": first_action.get("term"),

                    }

            if goals_added:

                summary["success_plan"]["samples"] = goals_added[:3]

        except Exception as exc:

            summary["success_plan_error"] = repr(exc)

            actions = []



        control_actions: List[Dict[str, Any]] = []

        if actions:

            try:

                control_actions = self._execute_plan_actions(actions)

                if control_actions:

                    summary["control_actions"] = control_actions

            except Exception as exc:  # pragma: no cover - defensive logging

                summary["control_actions_error"] = repr(exc)



        bug_info = self._run_bug_scan(summary)

        heal_info = self._run_self_heal(summary)

        tests_info = self._run_tests()

        git_info = self._git_status()



        entry = {

            "timestamp": self._now(),

            "status": "completed",

            "summary": summary,

            "bug_scan": bug_info,

            "self_heal": heal_info,

            "tests": tests_info,

            "git": git_info,

            "forced": force,

        }

        self._record(entry)





def govern() -> None:

    """Entry point for the processing manager."""



    AutonomyController().govern()





def force_govern() -> None:

    """Force a governance cycle, bypassing the cooldown."""



    AutonomyController().govern(force=True)





__all__ = ["AutonomyController", "govern", "force_govern"]

