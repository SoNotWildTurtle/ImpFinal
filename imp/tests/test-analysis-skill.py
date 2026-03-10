from pathlib import Path
import importlib.util
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT.parent / "skills" / "analysis_skill.py"

spec = importlib.util.spec_from_file_location("analysis_skill", SCRIPT)
module = importlib.util.module_from_spec(spec)
sys.modules["analysis_skill"] = module
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as temp_dir:
    base = Path(temp_dir)
    (base / "tests").mkdir()
    (base / "app.py").write_text("import os\nprint('hello')\n")
    (base / "module.py").write_text("# TODO: add function\n")
    (base / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n")
    (base / "requirements.txt").write_text("requests\n")

    config = module.AnalysisConfig(root=base, max_files=1000)
    report = module.analyze_repository(config)

    missing = {item["path"] for item in report.missing_tests}
    assert "module.py" in missing, "module.py should be flagged as missing test"
    assert "app.py" not in missing, "app.py test should be detected"
    assert report.dependencies.get("requirements.txt"), "requirements should be parsed"
    assert report.todos, "TODOs should be recorded"
    assert report.test_coverage["coverage_percent"] < 100.0, "coverage should drop for missing tests"
    assert report.test_coverage["referenced_modules"] >= 0, "referenced modules should be tracked"
    assert report.dependency_summary["top_python_imports"], "imports should be summarized"
    assert report.scan_stats["elapsed_seconds"] >= 0, "scan stats should be recorded"

print("Analysis Skill Test Passed!")
