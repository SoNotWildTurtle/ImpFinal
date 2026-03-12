from __future__ import annotations

from imp.runtime import IMP_ROOT, load_module


_MODULE = load_module(
    "imp_operator_dashboard_dash",
    IMP_ROOT / "core" / "imp-operator-dashboard.py",
)

main = _MODULE.main


if __name__ == "__main__":
    raise SystemExit(main())

