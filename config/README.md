# IMP Config Compatibility Directory

The canonical runtime configuration lives under `imp/config/`.

This top-level `config/` directory exists so repo-level docs, audits, and operator tooling have a stable path to point at from the repository root. Do not treat it as the primary source of runtime JSON files unless a wrapper explicitly says so.

Use `imp/config/` for active configuration such as:

- `imp-config-manager.py`
- `imp-cluster-nodes.json`
- `imp-system-settings.json`
- `imp-personality.json`
