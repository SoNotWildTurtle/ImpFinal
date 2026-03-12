from __future__ import annotations

from imp.runtime import IMP_ROOT, load_module


_MODULE = load_module("imp_execute_dash", IMP_ROOT / "core" / "imp-execute.py")

build_manager = _MODULE.build_manager
init_networks = _MODULE.init_networks
main = _MODULE.main


if __name__ == "__main__":
    main()

