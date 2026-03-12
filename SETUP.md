# IMP Setup Guide

This guide walks an operator through the first pass bootstrap of IMP.

## 1. Obtain the code
Clone this repository into a working directory you control. Startup scripts resolve the repository root dynamically.

## 2. Install and launch
Run `bash bin/imp-install.sh` from the repository root. `bash imp/bin/imp-install.sh` remains valid if you prefer the implementation path.
- Installs Python requirements from `requirements.txt`. If the global install fails, the script creates a local `.venv` and installs there.
- Downloads a baseline GGUF model into `imp/models` (unless one already exists or `IMP_SKIP_GGUF_DOWNLOAD` is set). Set `IMP_GGUF_URL` to override the default StarCoder2 link.
- Starts `imp/bin/imp-start.sh`, which now delegates to the Python supervisor at `imp/bin/imp-start.py`.
- Direct Python fallback: `python -m imp.bin.imp_start`

## 3. Verify a chat terminal
Kali WSL terminals may close unexpectedly. Run `bash bin/imp-verify-chat.sh` to confirm the goal chat process is alive. If it is missing, the script logs the event and restarts `imp-goal-chat.py`.
- Pass `--no-start` to log status without starting the chat.
- Logs are written to `imp/logs/imp-chat-keepalive.log`.

## 4. Configuration notes
Configuration files live under `imp/config`, and default log files live under `imp/logs` so tests can run immediately. Shell and PowerShell environment helpers now create missing `logs`, `config`, and `models` directories on startup.

## 5. Validation
- Canonical smoke check: `python tests/smoke.py`
- Alternate smoke wrapper: `python tests/run-all-tests.py --smoke`
- Broader suite: `bash tests/run-all-tests.sh`
- Quick runtime status: `bash bin/imp-status.sh`

## 6. Troubleshooting
- The start script resolves the repository root dynamically, prefers `.venv` when present, and records startup failures in `imp/logs/imp-start-runtime.log`.
- Startup state is summarized in `imp/logs/imp-start-state.json`.
- Modules fall back to offline behavior when external models are unavailable.
- Schedule `bin/imp-verify-chat.sh` via cron in Kali WSL if terminals frequently close.
- Test runners default to safe mode (`IMP_SAFE_TESTS=1`) and skip self-modifying tests. Set `IMP_SAFE_TESTS=0` only when you intentionally want updater/self-healer rewrite tests to run.

## 7. Methodology Profile
- Planning and readiness modules read `imp/plan.json`.
- Keep this file aligned with `imp/notes/self-evolution-plan.txt`, `imp/notes/self-evolution-dev-notes.txt`, and `imp/notes/imp-developer-notes.txt` when extending module behavior.
- `imp/self-improvement/imp-module-operability.py` uses `operability_profiles` from `imp/plan.json` and writes audit history to `imp/logs/imp-module-operability.json`.
- If `operator_policy.auto_generate_operability_goals` is enabled in `imp/plan.json`, failed operability checks create deduplicated follow-up goals under `imp/logs/imp-goals.json`.

This document helps operators bootstrap IMP and ensure a chat terminal remains available during early setup.
