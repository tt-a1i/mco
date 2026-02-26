# Multi-CLI Orchestrator Proposal (Claude/Codex/Gemini/OpenCode/Qwen)

## 1) Product Positioning
Build a neutral orchestration layer for coding agents.

- Any provider can be the entrypoint.
- Any provider can be a downstream reviewer.
- Provider participation is dynamic based on user environment and policy.

This avoids single-vendor lock-in and supports mixed-tool teams.

## 2) Provider Adapter Contract
Treat each CLI as a plugin adapter:

- `claude`
- `codex`
- `gemini`
- `opencode`
- `qwen`

```ts
type ProviderId = "claude" | "codex" | "gemini" | "opencode" | "qwen";

interface CapabilitySet {
  tiers: Array<"C0" | "C1" | "C2" | "C3" | "C4" | "C5" | "C6">;
  supports_native_async: boolean;
  supports_poll_endpoint: boolean;
  supports_resume_after_restart: boolean;
  supports_schema_enforcement: boolean;
  min_supported_version: string;
  tested_os: Array<"macos" | "linux" | "windows">;
}

interface TaskRunRef {
  task_id: string;
  provider: ProviderId;
  run_id: string;
  pid?: number;              // shim async mode
  session_id?: string;       // native session mode
  artifact_path: string;
  started_at: string;
}

interface ProviderAdapter {
  id: ProviderId;
  detect(): Promise<ProviderPresence>;
  capabilities(): Promise<CapabilitySet>;
  run(input: TaskInput): Promise<TaskRunRef>;
  poll(ref: TaskRunRef): Promise<TaskStatus>;
  cancel(ref: TaskRunRef): Promise<void>;
  normalize(raw: unknown, ctx: NormalizeContext): NormalizedFinding[];
}
```

## 3) Capability Tiering Standard
Use capability tiers instead of binary yes/no support.

- `C0`: Binary + auth detection
- `C1`: Non-interactive execution
- `C2`: Structured JSON output (final result)
- `C3`: Streaming structured events
- `C4`: Session resume/continue
- `C5`: Schema-constrained output
- `C6`: Policy hooks/permissions/API control plane

Routing and SLOs should be based on these tiers, not provider names.

## 4) Initial Capability Matrix (Evidence-Based)
`Y` = supported in docs, `P` = partial/conditional (must pass probe before enabling), `N` = not documented.

| Provider | C1 | C2 | C3 | C4 | C5 | C6 | Native async | min_version (lock) | tested_os | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | Y | Y | Y | Y | Y | Y | P | 2.1.59 (macos) | macos | Strong CLI/hook support; native job endpoint not primary mode |
| Codex CLI | Y | Y | Y | Y | Y | P | P | 0.46.0 (macos) | macos | `exec --json`, `resume`; async mostly process/session based |
| Gemini CLI | Y | Y | Y | P | N | Y | P | 0.1.7 (macos) | macos | Headless formats solid; resume semantics require probe |
| OpenCode | Y | Y | Y | Y | N | Y | Y | 1.2.11 (macos) | macos | `serve` provides native pollable interface |
| Qwen Code | Y | Y | P | Y | N | P | P | 0.10.6 (macos) | macos | `stream-json` output/input behavior varies by version; C3 passed with `qwen-oauth` auth mode |

Implementation rule:
- If task needs only `C1-C2`, all qualifying providers can run.
- If task requires native async polling, prefer providers with `supports_native_async=true`, else use shim polling.

Probe pass criteria (frozen before implementation):
- `C0`: binary found, version readable, auth check successful.
- `C1`: non-interactive fixture run yields expected completion token/output.
- `C2`: final output includes machine-parseable JSON content that passes shape validation.
- `C3`: stream mode emits >= 2 valid structured events on fixture task.
- `C4`: resume across fresh process works and context continuity is verified.
- `C5`: schema-constrained run rejects invalid schema and respects valid schema.
- `C6`: permission/policy constraints enforced in negative tests.

## 5) Runtime Discovery and User Config
### Discovery order
1. Load user config (`enabled`, roles, allowlist).
2. Probe binaries (`which claude`, `which codex`, etc.).
3. Run auth checks and capability probes.
4. Register healthy adapters with measured capabilities.

### Config example
```yaml
providers:
  claude:
    enabled: true
    role: [entrypoint, reviewer]
    weight: 1.0
    max_cost_usd: 0.8
    min_version: "2.1.59"
    tested_os: [macos]
  codex:
    enabled: true
    role: [entrypoint, reviewer]
    weight: 1.0
    max_cost_usd: 0.8
    min_version: "0.46.0"
    tested_os: [macos]
  gemini:
    enabled: true
    role: [reviewer]
    weight: 0.8
    max_cost_usd: 0.6
    min_version: "0.1.7"
    tested_os: [macos]
  opencode:
    enabled: true
    role: [reviewer]
    weight: 0.7
    max_cost_usd: 0.5
    min_version: "1.2.11"
    tested_os: [macos]
  qwen:
    enabled: true
    role: [reviewer]
    weight: 0.6
    max_cost_usd: 0.5
    min_version: "0.10.6"
    tested_os: [macos]

policy:
  required_capabilities: [C1, C2]
  optional_capabilities: [C3, C4, C5, C6]
  max_parallel_reviewers: 2
  budget_usd_per_task: 1.5
  timeout_seconds: 600
  provider_allowlist: [claude, codex, gemini, opencode, qwen]
```

## 6) Task State Machine and Idempotency
### Global task state
- `DRAFT` -> `QUEUED` -> `DISPATCHED` -> `RUNNING` -> `AGGREGATING` -> `COMPLETED`
- Retry branch: `RUNNING` -> `RETRYING` -> `RUNNING`
- Terminal states: `COMPLETED`, `PARTIAL_SUCCESS`, `FAILED`, `CANCELLED`, `EXPIRED`

### Provider attempt state
- `PENDING` -> `STARTED` -> `SUCCEEDED`
- `PENDING` -> `STARTED` -> `RETRYABLE_FAILED` -> `RETRYING` -> `STARTED`
- `PENDING` -> `STARTED` -> `NON_RETRYABLE_FAILED`
- `PENDING` -> `STARTED` -> `CANCELLED`

### Idempotency model
- `task_idempotency_key = hash(repo, revision, prompt, scope, policy_version)`
- Same key returns existing active task instead of creating a duplicate.
- `dispatch_key = hash(task_id, provider, attempt_no)` prevents duplicate fan-out.
- Artifact writes are atomic (`tmp` then rename).
- Notifications are deduped by `(task_id, terminal_state, channel)`.

### Partial success policy
- If at least one required provider succeeds and policy gates pass: `PARTIAL_SUCCESS`.
- If all required providers fail: `FAILED`.

### `EXPIRED` trigger and reaper
- Expire condition A: run wall-clock exceeds `timeout_seconds + grace_seconds`.
- Expire condition B: no heartbeat update for `heartbeat_ttl_seconds`.
- Reaper scan interval: every 60 seconds (configurable).
- Reaper compensation flow:
1. Try provider-native cancel if available.
2. If shim mode, send `SIGTERM`, wait 10 seconds, then `SIGKILL`.
3. Mark attempt/task `EXPIRED`, persist partial artifacts, emit terminal notification.
4. Apply retry policy only if attempt is marked retryable by adapter error classifier.

## 7) Async Execution Model and Poll Semantics
`poll(ref)` must work in both modes:

1. Native async mode (`supports_native_async=true`)
- Adapter submits run and gets provider-side `run_id/session_id`.
- `poll()` queries provider endpoint/session status.

2. Shim async mode (`supports_native_async=false`)
- Orchestrator starts CLI as OS process and tracks `pid`.
- Stdout/stderr are streamed to artifact files.
- `poll()` checks process state + heartbeat file + output completion marker.
- On process exit, adapter parses final artifact and maps terminal state.

Shim guarantees:
- Works for CLIs that are synchronous by design.
- Supports timeout, cancellation, and crash recovery via persisted run refs.

## 8) Capability-Gated Routing
Hard filters:
- Provider is enabled and allowlisted.
- Provider meets `required_capabilities`.
- Provider has not exceeded per-provider cost cap.
- Estimated run cost <= remaining task budget.

Scoring formula:
`score = capability_match * reliability_weight * user_weight / expected_cost`

Selection defaults:
- Low risk diff: top 1 reviewer
- Medium risk diff: top 2 reviewers
- High risk/security-tagged diff: top 3 reviewers (budget permitting)

## 9) Normalize Strategy (Critical Path)
`normalize()` is implementation-critical and provider-specific.

| Provider type | Strategy | Failure fallback |
| --- | --- | --- |
| Structured-output first (Claude/Codex when schema enabled) | Use JSON/schema mode, direct field mapping to canonical schema | If schema parse fails, rerun with strict JSON-only prompt once |
| JSON-capable but schema-weak (Gemini/OpenCode/Qwen in some modes) | Use structured prompt contract + JSON parser + repair pass | If repair fails, mark run as parse-failed and trigger text-parser fallback |
| Text-first outputs | Two-step extraction: text -> LLM extractor constrained to canonical schema | If extractor fails twice, keep raw artifact and emit `normalization_error` |

Prompt contract for extraction mode:
- Require array of findings with fixed keys.
- Require file path and line when available (`line` can be `null`).
- For unknown fields, return `null` instead of inventing values.

Normalization quality checks:
- Drop findings without category/severity/title.
- Clamp confidence to `[0,1]`.
- Validate file paths are inside repo root.

## 10) Canonical Finding Schema
```json
{
  "task_id": "string",
  "provider": "claude|codex|gemini|opencode|qwen",
  "finding_id": "string",
  "severity": "critical|high|medium|low",
  "category": "bug|security|performance|maintainability|test-gap",
  "title": "string",
  "evidence": {
    "file": "path",
    "line": null,
    "symbol": "optional symbol",
    "snippet": "string"
  },
  "recommendation": "string",
  "confidence": 0.0,
  "fingerprint": "stable hash",
  "raw_ref": "artifact pointer"
}
```

Schema note:
- `evidence.line` is nullable for providers that only return symbol/snippet-level evidence.

## 11) Dedupe and Conflict Resolution
`file+line+category` is stage-0 only. Use three-stage merge:

1. Exact fingerprint merge
- Normalized path + symbol + category + canonicalized title hash.

2. Proximity merge
- Same file + same category + line delta <= 5 + token similarity above threshold.

3. Semantic merge
- Embedding similarity above threshold and overlapping evidence snippets.

Conflict rules:
- Severity = max severity in cluster.
- Confidence = weighted average by provider reliability.
- Preserve per-provider evidence links for audit.

## 12) Security and Compliance Baseline
### Data egress controls
- Provider allowlist and per-project egress policy.
- Pre-send redaction for secrets/tokens/credentials/PII.
- Path filters (`include_paths`/`exclude_paths`) to minimize code exposure.

### Access controls
- Default read-only tool profile for review tasks.
- Provider-specific permission profiles; no implicit shell escalation.
- Global kill switch per provider.

### Audit and retention
- Immutable attempt log: actor, timestamps, provider, prompt hash, artifact hashes.
- Retention by class (`raw_artifacts`, `summaries`, `decision_log`).
- Traceability from merged findings to raw provider outputs.

### Compliance hooks
- Optional policy checks before dispatch (license/classification/region rules).
- Block dispatch if project policy requires local-only and provider is remote-only.

## 13) Artifact Generation Logic (summary.md / decision.md)
Frozen stage-A contract implementation:
- Adapter interface: `runtime/contracts.py`
- Artifact layout: `runtime/artifacts.py`

`summary.md` generation:
- Rule-based renderer from canonical findings.
- Includes counts by severity/category, provider coverage, and unresolved parse errors.

`decision.md` generation:
- Phase 1 (MVP): rule-based decision engine only.
- Decision rules: fail gate on `critical`, escalate on `high >= threshold`, else pass with follow-ups.
- Phase 2: optional AI-assisted synthesis pass (provider configurable), but final decision must include rule trace.

This keeps `decision.md` deterministic in early stages and auditable later.

Stage-A required per-task artifacts:
- `summary.md`
- `decision.md`
- `findings.json`
- `run.json`
- `providers/<provider>.json`
- `raw/<provider>.stdout.log`
- `raw/<provider>.stderr.log`

## 14) Risk Register and Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Output format divergence | Normalization failures | Adapter-specific normalize strategy + parse fallback + error taxonomy |
| Auth/config variation | Provider unavailable at runtime | `doctor` checks + setup guide + preflight validation |
| Cost overrun | Budget breach | Global budget + per-provider cap + auto fan-out downgrade |
| False dedupe or missed merge | Quality drop | 3-stage dedupe + sampled human audit + threshold tuning |
| Async instability | Orphaned runs | Native/shim poll model + heartbeat + timeout + restart recovery |

## 15) Realistic Delivery Plan
### Stage A (2 weeks): gate + core
- State machine, idempotency, artifact writer, notifier
- Adapter framework + capability probes
- Two providers only: `claude`, `codex`

### Stage B (2-3 weeks): expansion + security
- Add `gemini`, `opencode`
- Redaction, allowlist, audit logs
- Dedupe v2 (exact + proximity)

### Stage C (2 weeks): fifth provider + optimization
- Add `qwen`
- Semantic dedupe and conflict scoring
- Metrics dashboard + routing calibration

## 16) Implementation Gate Checklist
Do not start broad rollout until all pass, in this order:

1. Freeze capability probe pass/fail criteria for each `C` level and lock them in test fixtures.
2. Run adapter contract tests: input/output mapping, error taxonomy, retry semantics.
3. Run 2-provider dry run (`claude` + `codex`) to validate idempotency, state transitions, and artifact persistence chain.
4. Run state-machine suite (retries, duplicate submit, partial success, expired recovery).
5. Verify security baseline (redaction, allowlist, audit log).
6. Verify budget/latency policies in target environment.

## 17) Success Criteria by Stage
Stage A (leading indicators):
- >= 90% successful normalization on sampled runs
- zero duplicate notifications for duplicate submissions
- median latency for 1-provider review within target SLO

Stage B (operational quality):
- parse-failure rate < 5%
- budget overrun rate < 3%
- manual reviewer "useful" rating >= 4/5 on pilot tasks

Stage C (outcome metrics, 4-8 week pilot):
- >= 20% increase in accepted high-severity findings
- <= 15% increase in median feedback time
- measurable false-positive reduction after dedupe tuning
- < 3% task failure from adapter/runtime issues

If metrics miss targets, reduce fan-out depth and keep best-performing providers.

## 18) Sources and Known Uncertainties
Primary sources:
- Claude Code CLI and hooks docs
- OpenAI Codex CLI `exec`/non-interactive docs
- Gemini CLI headless and command argument docs
- OpenCode CLI and agents docs
- Qwen Code non-interactive/resume/output docs

Known uncertainty:
- Gemini headless resume behavior across process restarts is treated as partial until adapter probe confirms.
