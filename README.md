# IMP

IMP (Intelligent Management Platform) is a Python-heavy research/runtime sandbox with orchestration, self-improvement, security, and operator tooling. This repository is currently stabilized around a single reality:

- most implementation code lives under `imp/`
- root `bin/` and `tests/` are compatibility wrappers for the documented commands
- Windows startup is anchored at `imp-start.ps1`
- Unix startup is anchored at `bin/imp-start.sh`

See [SETUP.md](SETUP.md) for bootstrap details.

## Quick Start

1. Install dependencies:
   `bash bin/imp-install.sh`
2. Start IMP:
   Linux/macOS/WSL: `bash bin/imp-start.sh`
   Windows PowerShell: `.\imp-start-wrapper.ps1` or `.\imp-start.ps1`
   Direct Python fallback: `python -m imp.bin.imp_start`
3. Open the dashboard:
   `bash bin/imp-operator-dashboard.sh`
   or `python -m imp.core.imp_operator_dashboard`
4. Run baseline validation:
   `python tests/smoke.py`
   or `python tests/run-all-tests.py --smoke`

## Repository Reality

Unless otherwise noted, module paths below are relative to `imp/`.

- `imp/bin/`: real shell/PowerShell/Python entrypoints
- `bin/`: root-level wrapper scripts for common operator commands
- `imp/core/`: runtime orchestration, dashboards, analytics, planning, speech, mood, and neural helpers
- `imp/security/`: auditing, zero-trust, monitoring, auth, and defense helpers
- `imp/self-improvement/`: updater, self-healer, roadmap, readiness, and analysis tools
- `imp/expansion/`: node, queue, scheduler, and cluster helpers
- `imp/config/`: JSON configuration files
- `config/`: compatibility documentation for repo-root configuration references
- `imp/logs/`: runtime logs and persisted state used by many modules/tests
- `models/`: compatibility documentation for repo-root model references
- `imp/tests/`: implementation test suite
- `tests/`: root wrapper around the test runner

## Startup Model

- `bin/imp-start.sh` delegates to `imp/bin/imp-start.sh`, which delegates to the Python supervisor at `imp/bin/imp-start.py`.
- `imp-start.ps1` is the Windows bootstrapper. It resolves Python, prepares logs/config/models directories, validates OpenSSH support, and loops the same Python supervisor.
- `imp/bin/imp-start.ps1` is now only a delegating compatibility launcher.
- `imp/bin/imp-stop.py` is the canonical stop path. Shell and PowerShell stop scripts delegate to it.
- `bin/imp-status.sh` delegates to `imp/bin/imp-status.py`, which reports the active repo root, Python interpreter, state file, and PID metadata.
- Top-level `config/` and `models/` now exist as compatibility markers; runtime code still reads active assets from `imp/config/` and `imp/models/`.

## Important Commands

These root commands are intentionally available and forward into `imp/bin/`:

- `bin/imp-install.sh`
- `bin/imp-start.sh`
- `bin/imp-stop.sh`
- `bin/imp-status.sh`
- `bin/imp-operator-dashboard.sh`
- `bin/imp-verify-chat.sh`
- `bin/imp-chat-keepalive.sh`
- `bin/imp-readiness.sh`
- `bin/imp-success-plan.sh`
- `bin/imp-self-heal.sh`
- `bin/imp-defend.sh`
- `bin/imp-zero-trust.sh`
- `bin/imp-incident-report.sh`
- `bin/imp-control-hub.sh`
- `bin/imp-network-monitor.sh`
- `bin/imp-processing-report.sh`
- `bin/imp-processing-forecast.sh`
- `bin/imp-voice-menu.sh`
- `bin/imp-nn-menu.sh`

For less common utilities, use the implementation path under `imp/bin/`.

## Current Architecture

- Runtime orchestration: `core/imp-execute.py`, `core/imp-processing-manager.py`, `core/imp-processing-analytics.py`
- Operator interfaces: `core/imp-operator-dashboard.py`, `core/imp-goal-chat.py`, `core/imp-voice.py`, `core/imp-speech-to-text.py`
- Security: `security/imp-security-optimizer.py`, `security/imp-session-guard.py`, `security/imp-zero-trust-assessor.py`
- Self-improvement: `self-improvement/imp-code-updater.py`, `self-improvement/imp-self-healer.py`, `self-improvement/imp-general-intelligence-review.py`
- Expansion: `expansion/imp-cluster-manager.py`, `expansion/imp-load-scheduler.py`, `expansion/imp-distributed-queue.py`

## Testing

- Canonical smoke validation: `python tests/smoke.py`
- Full wrapper: `bash tests/run-all-tests.sh`
- Python wrapper: `python tests/run-all-tests.py`
- Python smoke wrapper: `python tests/run-all-tests.py --smoke`
- Startup/orchestration sanity checks live in:
  `imp/tests/test-start-script.py`,
  `imp/tests/test-stop-script.py`,
  `imp/tests/test-windows-support.py`,
  `imp/tests/test-execute-pipeline.py`,
  `imp/tests/test-launcher-bootstrap.py`,
  `imp/tests/test-status-script.py`,
  `imp/tests/test-smoke-runner.py`

`IMP_SAFE_TESTS=1` remains the default so self-modifying tests are skipped unless explicitly enabled.

## Logs And Diagnostics

- Application/runtime logs: `imp/logs/`
- Wrapper bootstrap logs: `logs/imp-start-wrapper-*.log`
- Startup state summary: `imp/logs/imp-start-state.json`
- PID metadata: `imp/logs/imp-pids.json`
- Quick status view: `bash bin/imp-status.sh`

## Current Status

This stabilization pass focused on reducing bootstrap and documentation chaos rather than adding new features:

- startup entrypoints are now more consistent across shell, Python, and PowerShell
- root-documented wrapper commands exist for the primary operator flows
- package-friendly module wrappers exist for the documented `python -m imp...` flows
- installer/bootstrap logic prefers the selected Python interpreter and local `.venv`
- docs now describe the actual repo layout instead of implying a root-level implementation tree

## Known Limitations

- The broad full/fast suite is still much heavier than the smoke path and may expose older module-level issues outside the bootstrap layer.
- The working tree may contain user-generated log changes under `imp/logs/`; those are not authoritative source files.
