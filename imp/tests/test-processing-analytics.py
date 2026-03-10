import importlib.util
import json
import subprocess
import unittest
import sys
from pathlib import Path


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestProcessingAnalytics(unittest.TestCase):
    def setUp(self):
        core_dir = Path(__file__).resolve().parents[1] / "core"
        self.analytics = _load("imp_processing_analytics", core_dir / "imp-processing-analytics.py")
        self.log_path = Path(__file__).resolve().parents[1] / "logs" / "imp-processing-log.json"
        if self.log_path.exists():
            self.original = self.log_path.read_text()
        else:
            self.original = None

    def tearDown(self):
        if self.original is None:
            if self.log_path.exists():
                self.log_path.unlink()
        else:
            self.log_path.write_text(self.original)

    def test_generate_processing_report(self):
        events = [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "event": "cycle",
                "group": "analysis",
                "duration": 2.0,
                "threads": 2,
                "errors": 0,
                "resource_score": 60,
                "backlog": 3,
            },
            {
                "timestamp": "2025-01-01T00:05:00Z",
                "event": "cycle",
                "group": "analysis",
                "duration": 3.0,
                "threads": 3,
                "errors": 1,
                "resource_score": 40,
                "backlog": 5,
            },
            {
                "timestamp": "2025-01-01T00:10:00Z",
                "event": "cloud_orchestration",
                "group": "analysis",
                "data": {"recommended_interval": 90},
            },
            {
                "timestamp": "2025-01-01T00:15:00Z",
                "event": "remote_dispatch",
                "group": "analysis",
                "tasks": ["echo run"],
                "interval": 120,
            },
        ]
        self.log_path.write_text(json.dumps(events, indent=2))

        report = self.analytics.generate_processing_report(limit=10)
        self.assertIn("analysis", report["groups"])
        metrics = report["groups"]["analysis"]
        self.assertEqual(metrics["cycles"], 2)
        self.assertAlmostEqual(metrics["average_duration"], 2.5)
        self.assertAlmostEqual(metrics["error_rate"], 0.5)
        self.assertIn("health_score", metrics)
        self.assertIn("health_status", metrics)
        self.assertEqual(metrics["max_backlog"], 5)
        self.assertIn("throughput_per_hour", metrics)
        self.assertIn("backlog_trend", metrics)
        self.assertIn("backlog_sparkline", metrics)
        self.assertEqual(report["remote_dispatch_count"], 1)
        self.assertGreater(len(report["recommendations"]), 0)
        self.assertTrue(any("analysis" in rec for rec in report["recommendations"]))
        self.assertIn("action_plan", report)
        self.assertTrue(report["action_plan"])  # plan should highlight analysis group
        overall = report.get("overall_health")
        self.assertIsNotNone(overall)
        self.assertIn("score", overall)

        snapshot = self.analytics.processing_health_snapshot(limit=10)
        self.assertIn("overall_health", snapshot)
        self.assertIn("alerts", snapshot)
        self.assertIn("analysis", snapshot["groups"])
        self.assertIn("spotlight", snapshot)
        self.assertIn("action_plan", snapshot)
        self.assertIn("leaders", snapshot)
        self.assertIn("comparisons", snapshot)

        diagnostics = self.analytics.group_diagnostics("analysis", limit=10)
        self.assertEqual(diagnostics["group"], "analysis")
        formatted = self.analytics.format_group_diagnostics(diagnostics)
        self.assertIn("Diagnostics for group 'analysis'", formatted)

        plan = self.analytics.action_plan(limit=10)
        self.assertTrue(plan)
        formatted_plan = self.analytics.format_action_plan(plan)
        self.assertIn("Processing Action Plan", formatted_plan)
        self.assertIn(plan[0]["group"], formatted_plan)

        timeline = self.analytics.group_timeline("analysis", limit=10)
        self.assertEqual(len(timeline), 2)
        formatted_timeline = self.analytics.format_group_timeline("analysis", timeline)
        self.assertIn("Timeline for group 'analysis'", formatted_timeline)
        self.assertIn("Backlog sparkline", formatted_timeline)

        comparisons = self.analytics.processing_comparisons(limit=10, top=1)
        self.assertIn("top_performers", comparisons)
        formatted_compare = self.analytics.format_comparisons(comparisons)
        self.assertIn("Processing Comparisons", formatted_compare)
        self.assertTrue(comparisons["top_performers"])

        cli = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "core" / "imp-processing-analytics.py"),
                "--group",
                "analysis",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Diagnostics for group 'analysis'", cli.stdout)

        cli_actions = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "core" / "imp-processing-analytics.py"),
                "--actions",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Processing Action Plan", cli_actions.stdout)

        cli_timeline = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "core" / "imp-processing-analytics.py"),
                "--group",
                "analysis",
                "--timeline",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Timeline for group 'analysis'", cli_timeline.stdout)

        cli_compare = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "core" / "imp-processing-analytics.py"),
                "--compare",
                "--top",
                "1",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Processing Comparisons", cli_compare.stdout)


if __name__ == "__main__":
    unittest.main()
