# Adapter Contract Tests (Gate Artifact 2)

## 1) Purpose
Define a uniform contract test suite for provider adapters:

- `claude`
- `codex`
- `gemini`
- `opencode`
- `qwen`

The suite validates input/output behavior, error taxonomy, and retry semantics.

## 2) Contract Under Test
Methods under test:
- `detect()`
- `capabilities()`
- `run(input)`
- `poll(ref)`
- `cancel(ref)`
- `normalize(raw, ctx)`

## 3) Test Harness Requirements
- Deterministic fixture repos and prompts.
- Per-provider sandbox workspace.
- Standardized artifact capture:
- `artifacts/<provider>/<test_case>/stdout.log`
- `artifacts/<provider>/<test_case>/stderr.log`
- `artifacts/<provider>/<test_case>/result.json`

## 4) Test Matrix

## A. `detect()`
Cases:
1. Binary exists + auth ok.
2. Binary missing.
3. Auth expired/invalid.

Expected:
- Returns structured provider presence object.
- Distinguishes `missing_binary` vs `auth_error`.

## B. `capabilities()`
Cases:
1. Fresh probe-derived capability set.
2. Unsupported feature path (for `P` capabilities).

Expected:
- `tiers` and booleans match lock summary.
- Includes `min_supported_version` and `tested_os`.

## C. `run(input)`
Cases:
1. Valid task with required capabilities.
2. Task requiring unsupported capability.
3. Invalid input schema.

Expected:
- Returns `TaskRunRef` with stable `run_id`.
- Rejects unsupported capability before dispatch.
- Input validation errors are non-retryable.

## D. `poll(ref)` (native async + shim async)
Cases:
1. Running state progression.
2. Completion state.
3. Process crash / lost heartbeat.
4. Unknown `run_id`.

Expected:
- Correct task state transitions.
- Shim mode maps PID/process signals to lifecycle states.
- Unknown references return `NON_RETRYABLE_FAILED`.

## E. `cancel(ref)`
Cases:
1. Cancel running native async job.
2. Cancel shim process.
3. Cancel completed run (idempotent cancel).

Expected:
- Running jobs reach `CANCELLED`.
- Completed jobs remain terminal without regression.

## F. `normalize(raw, ctx)`
Cases:
1. Valid structured JSON.
2. JSON with missing optional fields (`line` null).
3. Text fallback extraction.
4. Malformed output.

Expected:
- Output matches canonical schema.
- `evidence.line` may be `null`.
- Malformed data produces `normalization_error` classification.

## G. Error Taxonomy
All adapter errors must map into:
- `retryable_timeout`
- `retryable_rate_limit`
- `retryable_transient_network`
- `non_retryable_auth`
- `non_retryable_invalid_input`
- `non_retryable_unsupported_capability`
- `normalization_error`

No raw provider-specific error should escape without mapping.

## H. Retry Semantics
Rules:
1. Retryable errors: max 2 retries with exponential backoff.
2. Non-retryable errors: fail fast.
3. Duplicate dispatch guarded by `dispatch_key`.

Validation:
- Assert exact retry count and delay windows.
- Assert no duplicate final artifacts.

## 5) Gate Pass Criteria
Per provider:
- 100% pass for mandatory cases: A1, B1, C1, C2, D1, D2, E1, F1, G, H.
- No unknown error taxonomy buckets.
- No state regression from terminal states.

Cross-provider:
- Same fixture task yields parseable normalized findings for all enabled providers.
- Contract test report is generated in unified schema.

## 6) Required Deliverables
- `reports/adapter-contract/<date>/summary.md`
- `reports/adapter-contract/<date>/matrix.json`
- `reports/adapter-contract/<date>/failures/<provider>.md`

Gate decision is blocked if any mandatory case fails.
