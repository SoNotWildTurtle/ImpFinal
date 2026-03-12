from __future__ import annotations

from imp.runtime import IMP_ROOT, load_module


_MODULE = load_module("imp_status_dash", IMP_ROOT / "bin" / "imp-status.py")
main = _MODULE.main


if __name__ == "__main__":
    raise SystemExit(main())
