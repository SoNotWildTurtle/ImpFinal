import os
from pathlib import Path
import unittest

class TestBinScripts(unittest.TestCase):
    def test_scripts_executable(self):
        bin_dir = Path(__file__).resolve().parents[1] / "bin"
        for script in bin_dir.iterdir():
            with self.subTest(script=script.name):
                self.assertGreater(script.stat().st_size, 0, f"{script.name} is empty")
                if script.suffix == ".sh":
                    self.assertTrue(os.access(script, os.X_OK), f"{script.name} not executable")

if __name__ == "__main__":
    unittest.main()
