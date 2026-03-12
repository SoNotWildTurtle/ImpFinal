# AGENTS Instructions

This repository hosts the IMP project. Follow these guidelines when contributing or interacting via automated agents.

## Goals
- Keep the codebase stable and portable. Use relative paths and avoid system-specific dependencies whenever possible.
- Preserve history with additive changes. Do not remove features without a clear reason and a path to recovery.
- Run `python tests/smoke.py` before every commit for a fast bootstrap sanity check. Run `bash tests/run-all-tests.sh` when you need the broader wrapper-driven suite.

## Dev Notes
- Wrapper bootstrap logs live in the top-level `logs` directory. Runtime state, persisted JSON files, and most test fixtures live under `imp/logs`.
- Scripts in `bin` are entry points for launching and managing the system. They should remain lightweight and avoid hard-coded paths.
- The code updater supports both online and offline modes. Runtime models live under `imp/models`; the top-level `models/` directory is only a compatibility landing zone for repo-level guidance.

## Personal Notes
- The `notes` folder contains design ideas, research plans and reflections to guide IMP's evolution. Updates here inform goal planning and future development.
- New personal notes or goals should reference existing notes when relevant to maintain continuity.

By following these guidelines, AI agents and human contributors can coordinate effectively as IMP grows.
