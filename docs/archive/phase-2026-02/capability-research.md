# Capability Research Notes (Checked on 2026-02-26)

## Scope
Research goal: validate automation capabilities for five CLIs used by the orchestrator:

- Claude Code
- Codex CLI
- Gemini CLI
- OpenCode
- Qwen Code

## Evidence Summary

| Provider | Verified claims | Primary source |
| --- | --- | --- |
| Claude Code | Supports non-interactive prompt mode, `json` and `stream-json` output, resume option, schema-constrained output, hooks including session-end/notification style events | https://docs.anthropic.com/en/docs/claude-code/cli-reference and https://docs.anthropic.com/en/docs/claude-code/hooks |
| Codex CLI | Supports non-interactive `exec`, JSON event output, output schema, and explicit resume command | https://developers.openai.com/codex/noninteractive and https://developers.openai.com/codex/cli/reference |
| Gemini CLI | Supports headless mode with text/json/stream-json outputs; command arguments include resume flag `-r` | https://geminicli.com/docs/cli/headless/ and https://geminicli.com/docs/cli/configuration/#command-line-arguments |
| OpenCode | Supports non-interactive `run`, JSON output modes, session continue/session id, and API server mode; agents docs include permission controls | https://opencode.ai/docs/cli/ and https://opencode.ai/docs/agents/ |
| Qwen Code | Supports non-interactive mode, output formats (`text`, `json`, `stream-json`), and resume/continue options in headless mode docs | https://qwenlm.github.io/qwen-code-docs/en/users/features/headless/ |

## Uncertainties and Probe Plan

1. Gemini resume semantics in strict headless batch workflows need runtime probe.
- Risk: docs show resume flags, but restart and session persistence behavior should be validated in adapter tests.

2. Provider-specific schema guarantees vary.
- Risk: some providers document JSON output but not strict JSON schema enforcement.

3. Streaming payload shape differs across providers.
- Risk: event normalization layer must treat stream records as provider-specific before canonical mapping.

4. Some historical versions showed flag mismatch for `--output-format` in Qwen issues.
- Risk: capability probe must validate current installed version behavior before enabling C2/C3.

## Adapter Probe Checklist

For each provider, run these probes before enabling in production:

1. Detect probe
- Binary available, version fetchable, auth valid.

2. Output probe
- Non-interactive run returns parseable JSON with expected top-level keys.

3. Resume probe
- Start session, resume in new process, confirm history continuity.

4. Failure probe
- Inject invalid prompt/path and classify retryable vs non-retryable errors.

5. Policy probe
- Verify tool permission behavior matches adapter policy profile.
