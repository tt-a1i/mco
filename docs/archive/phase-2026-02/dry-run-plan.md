# Two-Provider Dry Run Plan (Gate Artifact 3)

## 1) Goal
Validate end-to-end gate path with `claude + codex` before expanding to more providers.

What must be proven:
- Idempotency works.
- State transitions are correct.
- Artifact persistence chain is complete.
- Notifications are deduplicated.

## 2) Scope
In scope:
- Single repo dry run on fixed commit.
- Two providers in parallel (`claude`, `codex`).
- One duplicate submission and one forced timeout scenario.

Out of scope:
- Full cost optimization.
- Multi-day production soak.

## 3) Preconditions
- Capability probes passed for `claude` and `codex` (`C0`, `C1`, `C2` minimum).
- Adapter contract mandatory cases passed.
- Redaction and allowlist policies enabled.

## 4) Test Inputs
- `repo`: fixture or pilot repo
- `revision`: fixed commit SHA
- `prompt`: fixed review prompt template
- `scope`: fixed file set
- `policy_version`: pinned

Generate deterministic idempotency key from these values.

## 5) Execution Steps

## Run A: Baseline successful run
1. Submit task once with both providers enabled.
2. Verify states:
- `QUEUED -> DISPATCHED -> RUNNING -> AGGREGATING -> COMPLETED|PARTIAL_SUCCESS`
3. Verify artifacts:
- `summary.md`
- `decision.md`
- `providers/claude.json`
- `providers/codex.json`
- `audit-log.json`
4. Verify one terminal notification sent.

## Run B: Duplicate submission test
1. Resubmit same task input (same idempotency key) within active window.
2. Expect orchestrator returns existing task reference.
3. Verify:
- No duplicate dispatch keys.
- No duplicate provider runs.
- No duplicate terminal notifications.

## Run C: Expired/recovery path
1. Submit a run with reduced timeout and induced long-running behavior.
2. Confirm reaper marks attempt/task as `EXPIRED`.
3. Confirm compensation:
- native cancel or shim termination path executed
- partial artifacts preserved
- terminal notification emitted once

## 6) Validation Checklist
- Idempotency:
- same key -> same task id
- duplicate submit does not spawn new attempts

- State machine:
- all transitions legal
- no transition from terminal -> non-terminal

- Persistence:
- all expected artifacts exist
- artifact writes are atomic (no partial JSON)

- Notification:
- exactly one terminal notification per `(task_id, terminal_state, channel)`

- Dedupe/normalize:
- normalized findings parse successfully
- schema-valid with nullable `evidence.line`

## 7) Pass/Fail Criteria
PASS:
- Run A, B, C all meet checklist with zero P0 failures.

FAIL:
- Any duplicate dispatch/notification.
- Missing mandatory artifact.
- Invalid state transition.
- Unclassified adapter error.

## 8) Deliverables
- `reports/dry-run/<date>/execution-log.md`
- `reports/dry-run/<date>/state-transition.json`
- `reports/dry-run/<date>/idempotency-check.json`
- `reports/dry-run/<date>/artifacts-manifest.json`
- `reports/dry-run/<date>/gate-decision.md`

Gate opens only if dry-run `gate-decision.md` is `PASS`.
