from __future__ import annotations

from imp.runtime import IMP_ROOT, load_module


_MODULE = load_module("imp_stop_dash", IMP_ROOT / "bin" / "imp-stop.py")
main = _MODULE.main


if __name__ == "__main__":
    raise SystemExit(main())
