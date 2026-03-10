# IMP Recommendations

This living document tracks actionable recommendations for improving IMP. Each recommendation lists follow-up notes so progress and context stay connected to the codebase.

## Recommendation 1: Expand capability visibility in the control hub
- **Status:** Completed
- **Notes:**
  - Added a CLI helper to inspect a single capability together with supporting agents.
  - Recorded the change in tests so regressions are caught quickly.

## Recommendation 2: Persist actionable plan history for operators
- **Status:** Completed
- **Notes:**
  - Plan submissions and approvals now write structured history records that surface through the CLI.
  - History entries include timestamps and metadata for future analytics.

## Recommendation 3: Surface queued plan summaries inside the chat terminal
- **Status:** Completed
- **Notes:**
  - Added a `/plans` command that lists queued plans with risk, confidence, and policy context.
  - Next iteration should weave the summary into the autonomy report for unified governance updates.

## Recommendation 4: Correlate processing analytics with control hub plans
- **Status:** Planned
- **Notes:**
  - Link plan history entries to processing group metrics to identify bottlenecks.
  - Emit cross-module alerts when a plan depends on degraded processing pools.

## Recommendation 5: Harden incident correlation with automated mitigations
- **Status:** Planned
- **Notes:**
  - Allow incident reports to trigger optional remediation playbooks via the control hub.
  - Log mitigations with the same immutable ledger infrastructure as self-healing events.

## Recommendation 6: Provide capability drift detection tooling
- **Status:** Planned
- **Notes:**
  - Periodically compare registered agent capabilities with recent execution logs.
  - Alert through the dashboard when an agent stops advertising a capability it used to own.

## Recommendation 7: Catalog risk drivers for high-variance plans
- **Status:** Planned
- **Notes:**
  - Enrich plan metadata with the top risk drivers detected by the security stack.
  - Feed those drivers into the processing analytics module for proactive scheduling tweaks.

## Recommendation 8: Expand identity verifier coverage for guardian recoveries
- **Status:** Planned
- **Notes:**
  - Simulate a guardian recovery event and ensure the verifier pipeline validates replacement credentials end-to-end.
  - Capture the recovery proof inside the incident correlator so operators can audit the flow later.

## Recommendation 9: Introduce concurrency budgets for neural evolution cycles
- **Status:** Planned
- **Notes:**
  - Track total CPU/GPU usage before triggering self-evolution to avoid starving live tasks.
  - Surface the concurrency budget inside the processing dashboard alongside existing action plans.

