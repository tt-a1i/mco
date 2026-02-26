# Capability Probe Spec (Gate Artifact 1)

## 1) Purpose
Define pass/fail rules for capability levels `C0-C6` for five providers:

- `claude`
- `codex`
- `gemini`
- `opencode`
- `qwen`

This spec is the source of truth for replacing `min_version: probe-lock`.

## 2) Scope
In scope:
- Capability verification
- Version/OS lock rules
- Probe artifacts and result schema

Out of scope:
- Business metric evaluation
- Full adapter implementation details

## 3) Probe Environment
Required test dimensions:
- OS: `macos`, `linux` (optional `windows` if target deployment includes it)
- Provider version: exact semver captured from CLI
- Network profile: normal connectivity

Test fixtures:
- `fixtures/repo-small` (5-20 files, includes known bug/security/test-gap samples)
- `fixtures/repo-medium` (50-200 files, includes refactor diffs)

## 4) Result Schema
Each probe run must emit one JSON record:

```json
{
  "provider": "claude|codex|gemini|opencode|qwen",
  "provider_version": "x.y.z",
  "os": "macos|linux|windows",
  "capability": "C0|C1|C2|C3|C4|C5|C6",
  "status": "PASS|CONDITIONAL_PASS|FAIL|SKIP",
  "reason": "short reason",
  "artifacts": {
    "stdout_path": "path",
    "stderr_path": "path",
    "parsed_output_path": "path"
  },
  "timestamp": "ISO-8601"
}
```

`CONDITIONAL_PASS` means capability only works under documented constraints and must be routed with guardrails.

## 5) Capability Pass/Fail Rules

## C0: Binary + Auth Detection
Steps:
1. Resolve binary from `PATH`.
2. Capture version.
3. Run non-destructive auth check.

PASS:
- Binary exists.
- Version parse succeeds.
- Auth check succeeds.

FAIL:
- Missing binary, unreadable version, or auth failure.

## C1: Non-Interactive Execution
Steps:
1. Run fixture prompt in non-interactive mode.
2. Capture exit code and duration.

PASS:
- Exit code `0`.
- Completion within timeout.

FAIL:
- Non-zero exit, hang, or timeout.

## C2: Structured JSON Final Output
Steps:
1. Run with provider JSON output mode.
2. Parse output as JSON (or normalized JSONL final object).
3. Validate required keys.

PASS:
- Parse succeeds and required fields present.

CONDITIONAL_PASS:
- Parse succeeds only with strict prompt contract or one repair pass.

FAIL:
- Unparseable output after one retry.

## C3: Streaming Structured Events
Steps:
1. Run in stream JSON mode.
2. Validate event sequence and parse each event.

PASS:
- At least 2 valid structured events emitted before completion.

CONDITIONAL_PASS:
- Stream shape valid only in specific version/profile.

FAIL:
- No structured events or malformed stream.

## C4: Resume/Continue Across Process Restart
Steps:
1. Start session/run and persist reference.
2. Kill client process.
3. Resume in fresh process.
4. Verify context continuity on follow-up prompt.

PASS:
- Resume works and continuity assertion passes.

CONDITIONAL_PASS:
- Resume works only within same machine/session constraints.

FAIL:
- Resume command unavailable or continuity lost.

## C5: Schema-Constrained Output
Steps:
1. Run with valid schema.
2. Run with intentionally invalid schema.

PASS:
- Valid schema respected.
- Invalid schema rejected with explicit error.

CONDITIONAL_PASS:
- Schema partially enforced (extra keys allowed) but required keys stable.

FAIL:
- No schema enforcement signal.

## C6: Policy/Permission Control
Steps:
1. Apply restrictive policy profile (read-only / tool denial).
2. Run prompt that attempts blocked operation.
3. Validate deny behavior.

PASS:
- Blocked operation is denied and logged.

CONDITIONAL_PASS:
- Denial works only in subset of execution modes.

FAIL:
- Policy ignored or bypassed.

## 6) Provider-Specific Caveat Mapping
- `claude`: expect strong `C2-C6`; native async is often shimmed by orchestrator process model.
- `codex`: `C6` may be mode-dependent; confirm permission behavior under non-interactive runs.
- `gemini`: `C4` requires strict restart probe before enabling resume-dependent routing.
- `opencode`: prefer native async probes via `serve` mode.
- `qwen`: treat `C3` as conditional until stream-json probe passes on locked version.

## 7) Version/OS Lock Rules
After probe batch:
1. For each provider/capability, keep only `PASS` or accepted `CONDITIONAL_PASS`.
2. Set `min_version` to the lowest version that passes all required capabilities (`C1`, `C2`) on each target OS.
3. Write lock table:

```yaml
provider_locks:
  claude:
    min_version:
      macos: "x.y.z"
      linux: "x.y.z"
    capabilities: [C0, C1, C2, C3, C4, C5, C6]
```

If Linux and macOS differ, keep per-OS locks.

## 8) Flake and Retry Policy
- Retry each failed probe once.
- If first fail + second pass: mark `CONDITIONAL_PASS` with `reason: flaky`.
- If both fail: `FAIL`.
- Any auth failure is non-retryable unless credentials changed.

## 9) Gate Decision Rules
Provider enablement:
- Must pass `C0`, `C1`, `C2`.
- `C3-C6` are opt-in by routing policy.

Task routing:
- If task requires capability `Cx`, provider must be `PASS` for `Cx`.
- `CONDITIONAL_PASS` allowed only when task policy explicitly enables conditional capabilities.

## 10) Output and Traceability
Store artifacts under:
- `docs/probes/YYYY-MM-DD/<provider>/<capability>/raw/`
- `docs/probes/YYYY-MM-DD/<provider>/<capability>/result.json`
- `docs/probes/YYYY-MM-DD/lock-summary.yaml`

Every gate decision must reference a concrete `result.json`.
