# IMP

IMP (Intelligent Management Platform) is a self-adapting research environment that combines multi-modal neural networks, autonomous planning, and layered security tooling.  It is designed to run entirely in Python across Linux or Windows systems while remaining portable, auditable, and recoverable.

The platform is organized into modular domains:

- **Runtime orchestration** – core services, neural networks, motivation/mood engines, planners, and task executors.
- **Self-improvement** – metacognitive analysis, blockchain-backed self healing, update pipelines, and experiment sandboxes.
- **Security & identity** – automated defenses, integrity monitoring, poisoning detection, communication hardening, and DID-based identity tooling.
- **Session assurance** – session guard analytics that evaluate live authentication trails, enforce MFA/idle policies, and surface threat-linked sessions for operator review.
- **Distributed expansion** – cluster management, remote task scheduling, intranet tooling, and cooperative memory queues.
- **Operator experience** – chat interface, dashboards, speech interfaces, readiness reviews, and goal/motivation workflows.
- **Reference assets** – setup guides, personal notes, research plans, identity specifications, and regression tests.

> See [SETUP.md](SETUP.md) for installation details, including dependency bootstrap, GGUF model download, and platform-specific launch steps.

---

## Quick Start
1. **Install dependencies:** `bash bin/imp-install.sh` or `bash imp/bin/imp-install.sh`. Both point to the same installer and create `.venv` if needed.
2. **Launch IMP:** `bash bin/imp-start.sh` on Unix-like systems or `.\imp-start-wrapper.ps1` / `.\imp-start.ps1` on Windows. The shell launcher now delegates to the Python supervisor in `imp/bin/imp-start.py`.
3. **Open the operator dashboard:** `bash bin/imp-operator-dashboard.sh` or `python -m imp.core.imp_operator_dashboard`.
4. **Run the verification suite:** `bash tests/run-all-tests.sh` or `python tests/run-all-tests.py`.

---

## Platform Setup Guides

### Linux (Ubuntu & Kali)
1. **System packages:** `sudo apt update && sudo apt install -y python3 python3-venv python3-pip git build-essential` (Kali already ships most tools, but run the command to ensure parity).
2. **Clone or update the repo:** `git clone` (or `git pull`) the IMP repository into a working directory you control.
3. **Run the installer:** from the repository root execute `bash bin/imp-install.sh`. The script creates/refreshes `.venv`, installs Python dependencies, and stages the baseline `models/starcoder2-15b.Q4_K_M.gguf` file.
4. **Start services:** launch `bash bin/imp-start.sh`. It resolves the project root dynamically, selects Python from `IMP_PYTHON`, `.venv`, `python3`, or `python`, then starts the Python supervisor. Use `bash bin/imp-operator-dashboard.sh` to access secondary tools.
5. **Kali-specific verification:** if you run inside a Kali WSL VM, keep the chat session persistent with `bash bin/imp-chat-keepalive.sh` (it falls back to `screen` when `tmux` is unavailable).

### Windows (PowerShell)
1. **Open an elevated PowerShell terminal** and enable execution of local scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
2. **Run the bootstrapper:** execute `./imp-start-wrapper.ps1` from the repository root to launch `imp-start.ps1` in a new terminal and stream logs back into the current session. The bootstrapper installs Python if missing, provisions dependencies via `bin/imp-install.sh` (through Git Bash or bundled MSYS tools), downloads the baseline GGUF model, prepares logs, ensures OpenSSH client/server services exist, and exports `IMP_REMOTE_DIR` for remote execution helpers.
3. **Persistent launch:** `imp-start.ps1` keeps IMP running in a guarded loop. You can alternatively call `python imp/bin/imp-start.py` or `python -m imp.bin.imp_start` once Python is installed; the script shares the same supervisor flow as the Unix helper.
4. **Operator dashboard:** from PowerShell run `bash bin/imp-operator-dashboard.sh` (Git Bash) or `python -m imp.core.imp_operator_dashboard` to access chat, self-heal, readiness, and security utilities.
5. **Post-install test:** invoke `bash bin/imp-verify-chat.sh` (Git Bash) or `python tests/run-all-tests.py` within the virtual environment to confirm the deployment is healthy. Logs are written under `imp/logs/` and root `logs/` wrapper outputs for parity.

---

## Major Capabilities

### Adaptive Intelligence
- Multi-network orchestration via `core/imp_neural_manager.py` with shared registries for general reasoning, 3D neural exploration, adversarial defenses, resource control, collaboratory planning, BCI dreamscapes, and network/security tasks.
- Mood, motivation, and goal systems that classify directives, prioritize by category, and close the loop through learning memory and strategy generators.
- An adaptive planner and motivation engine that fall back to local heuristics when ChatGPT access is unavailable.

### Self-Healing & Evolution
- Blockchain ledger (`self-improvement/imp-blockchain-ledger.py`) capturing file hashes or blob references with rotation.
- Self-healer (`self-improvement/imp-self-healer.py`) capable of linting, syntax checking, diff review, ledger restoration, ChatGPT recovery (with throttling), automatic minting, and patch generation.
- 3D neural network (`core/imp-3d-neural-network.py`) supporting experimental neuron types, dormancy/reactivation, angular routing, backup pathways, sandbox evolution, visualization exports, experiment logging, and blockchain-triggered restoration.
- General intelligence readiness reviews and success plans (`self-improvement/imp-general-intelligence-review.py`, `imp-success-director.py`) summarizing progress, regressions, and recommended goals.

### Security & Identity
- Automated defense orchestration, firewall hardening, network auditing, poison detection, process auditing, hardware guard, and cyber research routines under `security/`.
- Processing node security assessments (`security/imp-processing-security.py`) that cross-check allowlists, discovery diffs, suspicious connection audits, intranet membership, CIDR policies, and port restrictions before remote execution.
- Incident correlation (`security/imp-incident-correlator.py`, `bin/imp-incident-report.sh`) that fuses threat monitor alerts, network discovery diffs, and process audits into actionable incident reports under `logs/imp-incident-report.json` for operators and autonomy cycles.
- Identity toolkit (`identity/`) containing Solidity registries (v1/v2), issuer microservice scaffolding, SDKs for wallets/verifiers, BCI consent specifications, and integration tests.
- Secure command transformer (`communication/imp-command-transformer.py`) implementing nonce/HMAC “diamond handshake” sanitization for inter-agent messaging.
- Zero-trust assessor (`security/imp-zero-trust-assessor.py`, `bin/imp-zero-trust.sh`) that cross-checks session guard, processing security, host keys, and threat logs for zero-trust readiness.

### Distributed Processing
- Processing manager, controller, and optimizer neural nets (`core/imp-processing-manager.py`, `imp-processing-nn.py`, `imp-processing-optimizer-nn.py`) that coordinate process pools, telemetry collection, and adaptive scheduling with remote-node awareness.
- Node control utilities (`expansion/imp-node-control.py`, `imp-node-communicator.py`, `imp-load-scheduler.py`, `imp-distributed-queue.py`) for task distribution across trusted hosts with TLS messaging and cluster telemetry logs.
- Cloud orchestrator (`expansion/imp-cloud-orchestrator.py`) that ranks nodes by health/latency telemetry and tunes remote dispatch intervals.

### Operator Interfaces
- Terminal chat assistant (`core/imp-goal-chat.py`) with offline fallback, speech input, mode introspection, history review, personal notes surfacing, readiness to run in tmux/screen keepalive loops, and slash commands (`/goals`, `/mode`, `/history`, `/notes`, `/help`, `/mood`, `/clear`, `/quit`).
- Voice synthesis (`core/imp-voice.py`, `core/imp-voice-menu.py`, `bin/imp-voice.sh`) and speech recognition (`core/imp-speech-to-text.py`) with tone analysis and voice-signature verification.
- Operator dashboard (`core/imp-operator-dashboard.py` + `bin/imp-operator-dashboard.sh`) presenting the most-used management utilities.
- Success planning and readiness CLI wrappers (`bin/imp-readiness.sh`, `bin/imp-success-plan.sh`) for auditing GI progress.
- Processing analytics and forecasting (`core/imp-processing-analytics.py`, `core/imp_processing_forecaster.py`, `bin/imp-processing-report.sh`, `bin/imp-processing-forecast.sh`) that summarize telemetry, project upcoming load, and surface actionable follow-up items for each processing group.
- Session guard (`security/imp-session-guard.py`) with CLI integration to score active sessions, consult threat intelligence, and persist risk history under `logs/imp-session-guard.json`.
- Incident reporting (`bin/imp-incident-report.sh`) surfaced through the operator dashboard and chat autonomy flows so consolidated security findings remain one command away.

---

## Directory Reference
- **bin/** – Root compatibility wrappers that delegate to `imp/bin/` so documented commands work from the repository root.
- **communication/** – Secure alias transformer and design notes for the “diamond handshake” messaging protocol.
- **config/** – JSON configuration and credentials (environment paths, system settings, poison targets, OAuth, voice signatures, nodes, aliases, permissions). Managed via `config/imp-config-manager.py`.
- **core/** – Primary runtime modules: neural nets, planners, executors, dashboards, processing controllers, tone/mood/motivation, chat, voice, speech-to-text, status monitors, strategy generator, identity integration, learning memory, and network/defense engines.
- **expansion/** – Distributed workload utilities, intranet scaffolding, resource balancers, cluster manager, node monitoring/control, and experimental engines (e.g., game copilot, distributed memory).
- **identity/** – Smart contracts, issuer service, SDKs, wallet notes, and consent specifications supporting DID-based verification, revocation, and consent anchoring.
- **logs/** – Operational JSON/LOG/TXT files for goals, evolution, readiness, ledger, learning memory, roadmap progress, processing telemetry, neural experiments, tone, voice, chat keepalive, etc.
- **models/** – Stored neural weights, adversarial/defense/network models, and GGUF model placeholders. Installation fetches a default `starcoder2-15b.Q4_K_M.gguf` unless skipped.
- **notes/** – Research strategy, self-evolution plans, developer notes, cohesion issues, startup verification, blockchain self-healing notes, communication guides, and personal reflections.
- **security/** – Automated defense stack: authenticators, firewall manager, code lock, vulnerability scanner, poison detector, threat monitor, identity verifier, hardware guard, network auditors, process auditor, cyber researcher, processing-node security assessor, etc.
- **self-improvement/** – Update engine, code map, bug hunter, sandbox, trainers, metacognitive analysis, roadmap checker, blockchain ledger, self-healer, success director, neural testers, general intelligence review.
- **tests/** – Root compatibility wrappers for the test harness. The implementation suite lives under `imp/tests/` and can be run via either `tests/run-all-tests.sh` or `imp/tests/run-all-tests.sh`.

---

## Key Workflows

### Startup & Operation
1. **`bin/imp-start.sh` / `imp/bin/imp-start.py` / `imp-start.ps1`** – compute repository root, select a Python interpreter, launch the supervisor, persist PID metadata, and keep chat terminals alive via keepalive scripts.
2. **`core/imp-execute.py`** – registers networks with the neural manager, initializes processing groups, starts mood/goal/strategy engines, and delegates recurring work to the processing manager.
3. **`core/imp-processing-manager.py`** – spins up per-group processes, runs thread pools, gathers telemetry, consults the optimizer NN, dispatches remote tasks, and logs cycle metrics.
4. **`core/imp-processing-optimizer-nn.py`** – learns optimal thread counts, pauses, and launch order using historical telemetry and writes back recommendations.

### Self-Healing Cycle
1. **Ledger & Diffing** – `self-improvement/imp-blockchain-ledger.py` stores snapshot metadata and blob references. `imp-self-healer.py` computes hashes, detects mismatches, and logs diagnostics.
2. **Pre-injection checks** – syntax validation, linting (flake8 when available), bug-hunter scan, placeholder detection, and repository lock enforcement via `security/imp-code-lock.py`.
3. **Recovery steps** – prefer ledger restoration, fall back to ChatGPT (with throttling), record diffs and lint results, update logs, optionally mint new ledger entries.
4. **Verification** – run targeted or full tests, log outcome, update readiness metrics, and notify success director for goal planning.

### Identity & Consent Flow (Reference)
1. **Wallet** signs consent receipts and anchors hashes (EIP-712) when registering companions.
2. **Issuer service** verifies consent JWS, TEE quote, issues binding credential, and posts revocation roots and status bitmaps.
3. **Verifier SDK** checks issuer allowlist, verifies Merkle/bitmap proofs, and applies revocation policies.
4. **BCI simulator** demonstrates signed intent envelopes with liveness scores for future BCI integrations.

### Application Wiring Map

| Layer | Entrypoint(s) | Downstream Components | Outputs & Notes |
| --- | --- | --- | --- |
| Launch & orchestration | `bin/imp-start.sh`, `imp/bin/imp-start.py`, `imp-start.ps1` | `core/imp-execute.py` → `core/imp-processing-manager.py` → `core/imp-processing-optimizer-nn.py` | Bootstraps neural registries, scheduling pools, writes PID metadata, and emits startup logs under `imp/logs/`. |
| Operator experience | `bin/imp-operator-dashboard.sh`, `core/imp-operator-dashboard.py` | `core/imp-goal-chat.py`, readiness & success-plan CLIs, voice/tone modules | Unified terminal control surface; dispatches autonomy cycles, readiness reviews, and voice interactions. |
| Control hub | `bin/imp-control-hub.sh`, `core/imp-control-hub.py` | Goal manager, success director, policy registry, capability & agent catalogs | Conversational intent-to-plan bridge with policy evaluation, agent registration, queue approvals, and audit logging. |
| Security stack | `bin/imp-defend.sh`, `security/imp-security-optimizer.py`, `security/imp-session-guard.py` | Firewall/poison/process/network auditors, processing security assessor | Aggregates log state, session analytics, node attestations, and threat intelligence before remote execution. |
| Zero-trust posture | `bin/imp-zero-trust.sh`, `security/imp-zero-trust-assessor.py` | `config/imp-processing-security.json`, `config/imp-session-security.json`, threat logs | Audits policy flags, host keys, intranet membership, and threat logs to maintain zero-trust baselines. |
| Self-healing | `bin/imp-self-heal.sh`, `self-improvement/imp-self-healer.py` | `self-improvement/imp-blockchain-ledger.py`, `security/imp-code-lock.py`, integration tests | Performs lint/syntax checks, ledger restores, code generation, and verification runs with autonomy feedback. |
| Distributed processing | `core/imp-processing-manager.py`, `expansion/imp-cloud-orchestrator.py` | `expansion/imp-node-control.py`, `expansion/imp-distributed-queue.py`, intranet tooling | Balances local/remote workloads, updates node health summaries, and records analytics for forecasting dashboards. |

---

## Logging & Analysis Highlights
- `logs/imp-evolution-log.json` – evolution summaries (neurons, fitness, reactivations, reinforced links, snapshots, ledger actions).
- `logs/imp-general-intelligence-review.json` & `logs/imp-success-plan.json` – readiness metrics, regression guards, and follow-up objectives.
- `logs/imp-roadmap-progress.json` & `logs/imp-roadmap-progress-history.json` – coverage of roadmap goals and module directories over time.
- `logs/imp-processing-log.json` & `logs/imp-processing-optimizer.json` – telemetry and planner history for processing groups.
- `logs/imp-learning-memory.json` – categorized insights, status filtering, and trend logging for decision analysis.
- `logs/imp-tone-log.json`, `logs/imp-voice-log.txt` – tone classification, voice signature checks, and synthesized speech history.

---

## Testing
- Run the entire suite via `bash tests/run-all-tests.sh` or `python tests/run-all-tests.py`.
- Safe mode is enabled by default (`IMP_SAFE_TESTS=1`) so self-modifying tests are skipped unless explicitly opted in.
- To run self-modifying tests intentionally, use `python tests/run-all-tests.py --full --allow-self-modifying-tests` or set `IMP_SAFE_TESTS=0`.
- Individual modules mirror directory layout (e.g., `tests/test-identity-integration.py`, `tests/test-processing-manager.py`, `tests/test-self-healer.py`).
- Tests are additive; when adding features, extend or create matching tests and update the CohesionMap/notes if new files are introduced.

## Methodology Inputs
- `imp/plan.json` is the canonical methodology profile used by planning modules.
- It is derived from `notes/self-evolution-plan.txt`, `notes/self-evolution-dev-notes.txt`, `notes/imp-developer-notes.txt`, `notes/alex-comment.txt`, and `logs/imp-success-plan.json`.
- `core/imp-adaptive-planner.py` and `self-improvement/imp-success-director.py` read this profile for category, priority, and readiness targets.
- `self-improvement/imp-module-operability.py` reads `operability_profiles` from the same file and logs coverage checks to `logs/imp-module-operability.json`.
- When `operator_policy.auto_generate_operability_goals` is true, operability failures are converted into deduplicated short-term `operability` goals in `logs/imp-goals.json`.

---

## Additional References
- `SETUP.md` – environment preparation, installer details, PowerShell notes, Windows/Linux parity instructions.
- `notes/` – research roadmaps, personal reflections, next-generation strategy, blockchain self-healing approach, communication protocols, self-evolution methodology, cohesion tracking, and startup verification logs.
- `identity/` – comprehensive identity specification (`BCI_COMPANION_SPEC.md`), smart contracts, issuer microservice, SDKs, and wallet documentation.
- `communication/communication-notes.txt` – expanded explanation of the secure alias “diamond handshake”.
- `notes/project-structure.txt` and `CohesionMap.txt` – inventories of files, test coverage, and outstanding cohesion issues.

IMP is a continually evolving system; additive development, thorough logging, and regular test execution keep the project coherent and recoverable.
