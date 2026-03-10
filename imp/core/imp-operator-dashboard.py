#!/usr/bin/env python3
"""Interactive terminal dashboard and status view for IMP operators."""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import subprocess
from typing import Dict, Iterable, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE_DIR = ROOT / "core"


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


imp_utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = imp_utils.read_json

try:
    autonomy_module = _load(
        "imp_autonomy_controller", CORE_DIR / "imp-autonomy-controller.py"
    )
    AutonomyController = getattr(autonomy_module, "AutonomyController", None)
    AUTONOMY_LOG = getattr(
        autonomy_module, "AUTONOMY_LOG", ROOT / "logs" / "imp-autonomy-log.json"
    )
except Exception:  # pragma: no cover - autonomy controller missing
    AutonomyController = None
    AUTONOMY_LOG = ROOT / "logs" / "imp-autonomy-log.json"


MENU_GROUPS: List[Tuple[str, Dict[str, Tuple[str, List[str] | None]]]] = [
    (
        "Core Operations",
        {
            "1": (
                "Goal Chat",
                ["python3", str(ROOT / "core" / "imp-goal-chat.py")],
            ),
            "2": ("Self-Heal", ["bash", str(ROOT / "bin" / "imp-self-heal.sh")]),
            "3": (
                "Automated Defense",
                ["bash", str(ROOT / "bin" / "imp-defend.sh")],
            ),
            "4": (
                "Network Monitor",
                ["bash", str(ROOT / "bin" / "imp-network-monitor.sh")],
            ),
        },
    ),
    (
        "Processing Insights",
        {
            "5": (
                "Processing Summary",
                [
                    "python3",
                    str(ROOT / "core" / "imp-processing-analytics.py"),
                    "--summary",
                ],
            ),
            "6": (
                "Processing Report",
                ["python3", str(ROOT / "core" / "imp-processing-analytics.py")],
            ),
            "7": (
                "Processing Forecast",
                [
                    "python3",
                    str(ROOT / "core" / "imp_processing_forecaster.py"),
                    "--json",
                ],
            ),
            "8": (
                "Processing Diagnostics",
                None,
            ),
            "9": (
                "Processing Timeline",
                None,
            ),
            "10": (
                "Processing Comparison",
                None,
            ),
        },
    ),
    (
        "Tools",
        {
            "11": ("Voice Menu", ["bash", str(ROOT / "bin" / "imp-voice-menu.sh")]),
            "12": ("NN Menu", ["bash", str(ROOT / "bin" / "imp-nn-menu.sh")]),
            "13": ("Operator Success Plan", ["bash", str(ROOT / "bin" / "imp-success-plan.sh")]),
            "14": (
                "Processing Action Plan",
                [
                    "python3",
                    str(ROOT / "core" / "imp-processing-analytics.py"),
                    "--actions",
                ],
            ),
            "15": ("Run Autonomy Cycle", None),
            "16": ("Force Autonomy Cycle", None),
            "17": ("Autonomy History", None),
            "18": (
                "Generate Incident Report",
                ["bash", str(ROOT / "bin" / "imp-incident-report.sh")],
            ),
        },
    ),
]


def _iter_commands() -> Iterable[Tuple[str, str, List[str]]]:
    for _, commands in MENU_GROUPS:
        for key, (name, command) in commands.items():
            yield key, name, command


def list_options() -> None:
    for title, commands in MENU_GROUPS:
        print(f"[{title}]")
        for key, (name, _) in commands.items():
            print(f"  {key}. {name}")
        print("")


def _processing_status_lines() -> List[str]:
    try:
        analytics = _load(
            "imp_processing_analytics", CORE_DIR / "imp-processing-analytics.py"
        )
        snapshot = analytics.processing_health_snapshot(limit=100)
    except Exception:
        return ["Processing: status unavailable"]

    overall = snapshot.get("overall_health", {})
    lines = [
        "Processing health: score={score} status={status}".format(
            score=overall.get("score", "n/a"),
            status=overall.get("status", "unknown"),
        )
    ]
    spotlight = snapshot.get("spotlight") or []
    if spotlight:
        lines.append("  Focus groups: " + ", ".join(spotlight))
    leaders = snapshot.get("leaders")
    if leaders:
        lines.append("  Leaders: " + ", ".join(leaders))
    else:
        lines.append("  Leaders: none recorded")
    risks = snapshot.get("risk_groups")
    if risks:
        lines.append("  Needs attention: " + ", ".join(risks))
    else:
        lines.append("  Needs attention: none")
    groups = snapshot.get("groups", {})
    for name, metrics in sorted(groups.items()):
        lines.append(
            "  - {name}: score={score} status={status} backlog={backlog}".format(
                name=name,
                score=metrics.get("health_score", "n/a"),
                status=metrics.get("health_status", "unknown"),
                backlog=metrics.get("average_backlog", 0),
            )
        )
        sparkline = metrics.get("backlog_sparkline")
        if sparkline:
            lines.append(f"    backlog: {sparkline}")
        duration_spark = metrics.get("duration_sparkline")
        if duration_spark:
            lines.append(f"    duration: {duration_spark}")
        thread_spark = metrics.get("thread_sparkline")
        if thread_spark:
            lines.append(f"    threads : {thread_spark}")
    alerts = snapshot.get("alerts") or []
    if alerts:
        limited = alerts[:3]
        lines.append("  Alerts: " + "; ".join(limited))
        if len(alerts) > len(limited):
            lines.append(f"  (+{len(alerts) - len(limited)} more alerts via analytics)")
    action_plan = snapshot.get("action_plan") or []
    if action_plan:
        first = action_plan[0]
        lines.append(
            "  Next action [{priority}] {group}: {summary}".format(
                priority=first.get("priority", "info").upper(),
                group=first.get("group", "overall"),
                summary=first.get("summary", ""),
            )
        )
    return lines


def _autonomy_status_lines() -> List[str]:
    try:
        entries = read_json(AUTONOMY_LOG, [])
    except Exception:
        return ["Autonomy: status unavailable (log read error)."]

    if not isinstance(entries, list) or not entries:
        return ["Autonomy: no governance cycles recorded yet."]

    last = entries[-1]
    timestamp = last.get("timestamp", "unknown")
    status = last.get("status", "unknown")
    bug_scan = last.get("bug_scan") or {}
    issues = bug_scan.get("issues")
    self_heal = last.get("self_heal") or {}
    mismatches = self_heal.get("mismatches")
    summary = last.get("summary") if isinstance(last, dict) else {}
    goal_updates = summary.get("goal_updates") if isinstance(summary, dict) else {}
    success_plan = summary.get("success_plan") if isinstance(summary, dict) else {}
    tests = last.get("tests") if isinstance(last, dict) else {}
    git_info = last.get("git") if isinstance(last, dict) else {}
    forced = bool(last.get("forced"))
    fragments: List[str] = []
    if isinstance(goal_updates, dict) and goal_updates.get("count"):
        fragments.append(f"goals={goal_updates.get('count')}")
    if isinstance(success_plan, dict) and success_plan.get("actions"):
        fragments.append(f"actions={success_plan.get('actions')}")
    if issues is not None:
        fragments.append(f"bugs={issues}")
    if mismatches is not None:
        fragments.append(f"mismatches={mismatches}")
    if isinstance(tests, dict) and tests.get("success") is not None:
        fragments.append("tests=pass" if tests.get("success") else "tests=fail")
    git_changes = None
    git_clean = None
    if isinstance(git_info, dict):
        git_changes = git_info.get("changes")
        git_clean = git_info.get("clean")
        if git_changes is not None:
            fragments.append(f"git_changes={git_changes}")
        if git_clean is not None and git_clean is False:
            fragments.append("git_dirty")
    if forced:
        fragments.append("forced")
    fragment_text = " " + "[" + ", ".join(fragments) + "]" if fragments else ""
    lines = [f"Autonomy last run: {timestamp} ({status}){fragment_text}"]
    if isinstance(success_plan, dict):
        sample = success_plan.get("sample")
        if isinstance(sample, dict) and sample.get("goal"):
            lines.append(
                "  Next action: {goal} ({priority}, {term})".format(
                    goal=sample.get("goal"),
                    priority=sample.get("priority", "?"),
                    term=sample.get("term", "?"),
                )
            )
    if isinstance(tests, dict) and tests.get("success") is not None:
        status_text = "passed" if tests.get("success") else "failed"
        duration = tests.get("duration")
        duration_text = f" in {duration:.1f}s" if isinstance(duration, (int, float)) else ""
        lines.append(f"  Test suite {status_text}{duration_text}")
        if not tests.get("success") and tests.get("error"):
            lines.append(f"    error: {tests['error']}")
    return lines


def show_status_panel() -> None:
    for line in _processing_status_lines():
        print(line)
    for line in _autonomy_status_lines():
        print(line)
    print("")


def _processing_diagnostics_action() -> None:
    try:
        analytics = _load(
            "imp_processing_analytics", CORE_DIR / "imp-processing-analytics.py"
        )
    except Exception:
        print("Processing analytics module unavailable.")
        return

    snapshot = analytics.processing_health_snapshot(limit=200)
    groups = sorted(snapshot.get("groups", {}).items())
    if not groups:
        print("No processing telemetry recorded yet.")
        return

    print("Select a processing group for diagnostics:")
    for index, (name, metrics) in enumerate(groups, 1):
        score = metrics.get("health_score", "n/a")
        status = metrics.get("health_status", "unknown")
        print(f"  {index}. {name} (score {score}, {status})")
    choice = input("Enter number (blank to cancel): ").strip()
    if not choice:
        return
    try:
        selection = int(choice) - 1
    except ValueError:
        print("Invalid selection.")
        return
    if selection < 0 or selection >= len(groups):
        print("Selection out of range.")
        return
    group_name = groups[selection][0]
    diagnostics = analytics.group_diagnostics(group_name, limit=200)
    print(analytics.format_group_diagnostics(diagnostics))
    input("Press Enter to return to the menu.")


def _processing_timeline_action() -> None:
    try:
        analytics = _load(
            "imp_processing_analytics", CORE_DIR / "imp-processing-analytics.py"
        )
    except Exception:
        print("Processing analytics module unavailable.")
        return

    snapshot = analytics.processing_health_snapshot(limit=200)
    groups = sorted(snapshot.get("groups", {}).items())
    if not groups:
        print("No processing telemetry recorded yet.")
        return

    print("Select a processing group for timeline view:")
    for index, (name, metrics) in enumerate(groups, 1):
        score = metrics.get("health_score", "n/a")
        backlog = metrics.get("average_backlog", 0)
        print(f"  {index}. {name} (score {score}, backlog {backlog})")
    choice = input("Enter number (blank to cancel): ").strip()
    if not choice:
        return
    try:
        selection = int(choice) - 1
    except ValueError:
        print("Invalid selection.")
        return
    if selection < 0 or selection >= len(groups):
        print("Selection out of range.")
        return

    group_name = groups[selection][0]
    timeline = analytics.group_timeline(group_name, limit=200)
    print(analytics.format_group_timeline(group_name, timeline))
    input("Press Enter to return to the menu.")


def _processing_comparison_action() -> None:
    try:
        analytics = _load(
            "imp_processing_analytics", CORE_DIR / "imp-processing-analytics.py"
        )
    except Exception:
        print("Processing analytics module unavailable.")
        return

    comparisons = analytics.processing_comparisons(limit=200, top=5)
    print(analytics.format_comparisons(comparisons))
    input("Press Enter to return to the menu.")


CUSTOM_MESSAGE = "Press Enter to return to the menu."


def _autonomy_cycle_action(force: bool = False) -> None:
    if AutonomyController is None:
        print("Autonomy controller unavailable in this environment.")
        input(CUSTOM_MESSAGE)
        return

    try:
        controller = AutonomyController()
        controller.govern(force=force)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Autonomy cycle failed: {exc}")
        input(CUSTOM_MESSAGE)
        return

    for line in _autonomy_status_lines():
        print(line)
    if force:
        print("Forced autonomy cycle executed.")
    input(CUSTOM_MESSAGE)


def _autonomy_history_lines(limit: int = 5) -> List[str]:
    try:
        entries = read_json(AUTONOMY_LOG, [])
    except Exception:
        return ["Autonomy history unavailable (log read error)."]

    if not isinstance(entries, list) or not entries:
        return ["Autonomy history is empty."]

    output: List[str] = [f"Last {min(limit, len(entries))} autonomy cycles:"]
    for entry in entries[-limit:]:
        timestamp = entry.get("timestamp", "unknown")
        status = entry.get("status", "unknown")
        forced = " [forced]" if entry.get("forced") else ""
        output.append(f"- {timestamp} ({status}){forced}")
        summary = entry.get("summary")
        if isinstance(summary, dict):
            goal_updates = summary.get("goal_updates")
            if isinstance(goal_updates, dict) and goal_updates.get("count") is not None:
                output.append(f"    goals: {goal_updates.get('count')}")
            plan = summary.get("success_plan")
            if isinstance(plan, dict) and plan.get("actions") is not None:
                output.append(f"    actions: {plan.get('actions')}")
        tests = entry.get("tests")
        if isinstance(tests, dict) and tests.get("success") is not None:
            status_text = "passed" if tests.get("success") else "failed"
            output.append(f"    tests: {status_text}")
    return output


def _autonomy_history_action() -> None:
    for line in _autonomy_history_lines():
        print(line)
    input(CUSTOM_MESSAGE)


def _autonomy_cycle_action_normal() -> None:
    _autonomy_cycle_action(False)


def _autonomy_cycle_action_force() -> None:
    _autonomy_cycle_action(True)


CUSTOM_ACTIONS = {
    "8": _processing_diagnostics_action,
    "9": _processing_timeline_action,
    "10": _processing_comparison_action,
    "15": _autonomy_cycle_action_normal,
    "16": _autonomy_cycle_action_force,
    "17": _autonomy_history_action,
}


def run_menu() -> None:
    while True:
        show_status_panel()
        list_options()
        choice = input("Select an option (q to quit): ")
        if choice.lower() == "q":
            break
        command_entry = next(
            ((name, cmd) for key, name, cmd in _iter_commands() if key == choice),
            None,
        )
        if not command_entry:
            print("Invalid choice")
            continue
        name, command = command_entry
        if choice in CUSTOM_ACTIONS:
            CUSTOM_ACTIONS[choice]()
        elif command:
            subprocess.run(command)
        else:
            print(f"No command configured for {name}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="IMP operator dashboard")
    parser.add_argument("--list", action="store_true", help="List options and exit")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print the current status panel and exit",
    )
    args = parser.parse_args()
    if args.list:
        list_options()
    elif args.status:
        show_status_panel()
    else:
        run_menu()


if __name__ == "__main__":
    main()
