from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parent
MANAGER_PATH = ROOT / "core" / "imp-processing-manager.py"

spec = importlib.util.spec_from_file_location(__name__, MANAGER_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[__name__] = module
spec.loader.exec_module(module)
