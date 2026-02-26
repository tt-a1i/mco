# Notes: Multi-CLI Orchestration (Claude/Codex/Gemini/OpenCode/Qwen)

## Problem Reframe
- Target is not "Claude calls others", but "neutral orchestration where any supported CLI can be entrypoint or worker".
- User environments differ; provider availability must be dynamic and capability-driven.

## Non-Goals and Constraints
- Non-goal: building a hosted multi-tenant SaaS in v1; scope is local or single-team deployment.
- Non-goal: perfect semantic dedupe from day one; start with deterministic+heuristic hybrid.
- Constraint: support only five providers in initial scope (`claude`, `codex`, `gemini`, `opencode`, `qwen`).
- Constraint: adapters must run via official CLI contracts, not private reverse-engineered APIs.
- Constraint: provider availability is runtime-detected and user-configurable; no hard-required provider.

## Core Requirements
- Support exactly five providers first: `claude`, `codex`, `gemini`, `opencode`, `qwen`.
- Runtime discovery of installed/configured providers.
- Task execution can be asynchronous with completion notification.
- Multi-provider review results are persisted under docs directory with traceability.
- Avoid hard dependency on any single vendor-specific workflow.

## Architecture Principles
- Orchestrator core owns lifecycle, queue, retries, notifications, storage.
- Provider adapters are thin wrappers around CLI command contracts.
- Routing is policy-based (capability + cost + latency + confidence), not hardcoded.
- Output normalized into one canonical finding schema for cross-provider comparison.

## Risks
- Different output formats and stability across providers.
- Credential/auth setup varies by provider.
- Cost and latency increase with multi-provider fan-out.
- Finding deduplication and conflict resolution required.

## Evaluation Metrics
- Review acceptance rate by humans.
- Precision/false-positive rate by severity.
- Time-to-feedback and cost per reviewed change.
- Incremental value of 2nd/3rd provider (marginal gain).

## Glossary
- Provider Adapter: Wrapper that maps a specific CLI to the orchestrator interface.
- Capability Tier: Normalized maturity level of a provider for automation (JSON, resume, schema, etc.).
- Task ID: Stable orchestration identifier for one user request.
- Idempotency Key: Hash key used to deduplicate repeated submissions of the same task.
- Run Attempt: One provider execution attempt within a task.
- Partial Success: Task result where at least one required provider succeeded and policy allows completion.
