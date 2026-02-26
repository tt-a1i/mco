# Implementation Gate Checklist

## Gate Inputs
Required artifacts:
1. [capability-probe-spec.md](./capability-probe-spec.md)
2. [adapter-contract-tests.md](./adapter-contract-tests.md)
3. [dry-run-plan.md](./dry-run-plan.md)
4. [multi-cli-orchestrator-proposal.md](./multi-cli-orchestrator-proposal.md)

## Gate Sequence
1. Freeze probe criteria and run capability probes.
2. Fill provider version/OS lock table and replace `probe-lock`.
3. Run adapter contract tests on enabled providers.
4. Run two-provider dry run (`claude` + `codex`).
5. Verify security controls (redaction, allowlist, audit log).
6. Approve or block rollout.

## Decision Rules
Approve only when all conditions are true:
1. Required capabilities pass (`C0`, `C1`, `C2`) for enabled providers.
2. Contract tests pass mandatory cases.
3. Dry run reports `PASS`.
4. No duplicate dispatch/notification defects.
5. No unclassified error taxonomy.

Block rollout if any condition fails.

## Sign-Off Template
```md
Gate Decision: PASS|BLOCK
Date: YYYY-MM-DD
Reviewer:
Providers Enabled:
Version Locks:
Open Risks:
Follow-up Actions:
```
