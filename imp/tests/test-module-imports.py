import os
import platform
import subprocess
import sys
import unittest
from pathlib import Path


class TestModuleImports(unittest.TestCase):
    def test_all_modules_import(self):
        root = Path(__file__).resolve().parents[1]
        modules_dirs = ["core", "security", "self-improvement", "expansion"]
        skip_on_windows = {"imp-voice-menu.py"}
        skip_fast = {
            "imp-goal-chat.py",
            "imp-operator-dashboard.py",
            "imp-autonomy-controller.py",
            "imp-auto-heal.py",
            "imp-self-healer.py",
        }
        fast_mode = os.environ.get("IMP_FAST_TESTS") == "1"

        for sub in modules_dirs:
            for path in (root / sub).glob("*.py"):
                if platform.system() == "Windows" and path.name in skip_on_windows:
                    continue
                if fast_mode and path.name in skip_fast:
                    continue
                with self.subTest(module=path):
                    module_name = path.stem.replace("-", "_")
                    code = (
                        "import importlib.util, sys; "
                        f"spec=importlib.util.spec_from_file_location('{module_name}', r'{path}'); "
                        "mod=importlib.util.module_from_spec(spec); "
                        f"sys.modules['{module_name}']=mod; "
                        "spec.loader.exec_module(mod)"
                    )
                    try:
                        result = subprocess.run(
                            [sys.executable, "-c", code],
                            capture_output=True,
                            text=True,
                            timeout=15,
                            env=os.environ.copy(),
                        )
                    except subprocess.TimeoutExpired:
                        self.fail(f"Timed out while importing {path}")
                    if result.returncode != 0:
                        self.fail(
                            f"Failed to import {path} (exit {result.returncode})\n"
                            f"stdout:\n{result.stdout}\n"
                            f"stderr:\n{result.stderr}"
                        )


if __name__ == "__main__":
    unittest.main()
