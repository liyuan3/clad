# H001c — Windows Claude Runner (Codex decision)

## First: apply the exact outstanding functional regressions
adc9836 does NOT contain main a0cf95a. Codex ran docs/h001b_rereview_regressions.py unchanged on adc9836: 2 failed. Connection takeover fixes are a different issue.
Run git merge main in /home/fo/clad-hermes. Copy docs/h001b_rereview_regressions.py to tests/test_exact_functional_regressions.py and run it BEFORE editing. Do not replace its assertions. Fix these two cases, not extra hardening:
- Successful delivery with zero events, then disconnect -> not_found must NOT free device. Durable positive proof of NOT_CONNECTED is required; default False must not represent that proof.
- seq1 accepted, seq3 rejected, seq2 accepted -> done(last_seq=2) must NOT succeed. The server already knows seq3 existed. Persist the repair boundary, require seq3 replay before completion. Existing truncated-output test expectation is wrong; fix it.
Report before/after results of these exact tests. Migration edge hardening and rate limiting are deferred. Add only migrations needed for the functional fix, preserving data. Commit functional fixes separately.

## Decisions: no further environment/adapter clarification needed
Production target: one Windows computer or VM per platform account, with real installed Claude Code CLI. Codex can validate Windows separately. Linux fake adapter is for tests only, never acceptance of real execution.
First adapter: noninteractive Claude CLI; use installed-version-supported flags equivalent to claude -p --output-format stream-json --verbose --include-partial-messages. Check claude --help on the machine; use argument arrays and stdin for user prompts, not a shell-built command. Recover each conversation using its actual returned session_id and --resume. Use configured executable and workspace roots; do not copy login credentials.

## Scope and order
1. runner/ Python package with pair, run, doctor CLI. Pairing input interactive; token persisted locally, never printed/logged or committed. doctor reports executable/version/config readiness without secrets.
2. Outbound WS matching reviewed protocol, heartbeats, reconnect/backoff, single-instance/one-run guard. Durable SQLite journal: record run receipt BEFORE launching child; persist outbound events BEFORE sending; replay unacked events before terminal report. Never re-execute a journaled run on reconnect. Crash between launch/recording must be treated as unknown, not automatically relaunched.
3. Per-conversation persistent directory and Claude session mapping. First run captures session id; second prompt resumes it. Parse actual stream JSON including error/result events and exit code. Avoid duplicate text when both deltas and final message snapshots appear; tolerate split UTF-8/JSON lines. Keep stderr separate.
4. Cancellation controls owned child/process tree, with bounded graceful stop and Windows verification. Do not report cancelled merely because cancel was received. If process termination uncertain, preserve unknown. Handle repeated cancel on reconnect.
5. Explicit tool-permission configuration. No blanket bypass. If unattended approval cannot proceed, show actionable failure rather than hang. No arbitrary shell command passthrough.
6. Unit/integration tests with a deterministic fake CLI subprocess for session resume, partial output, errors, duplicate delivery, reconnect replay, cancellation and subprocess cleanup. Mark Linux-only verification clearly. Include Windows setup steps and a concise real-Claude smoke checklist.

Not this batch: installer, self-update, fleet scheduling, public deployment, artifact upload/download (remain []), rate limiting, exhaustive hardening. Do not edit frontend/. Do not spawn a real Claude request using paid credentials without the existing owner's configured environment and intended smoke task; report if unavailable rather than fabricate success.

Write docs/HERMES_REPORT_H001C.md with commands, verified behavior, test output and remaining limitations. Commit locally on hermes/backend-m1, let Codex review/push. Proceed into Runner once the two named regression tests and full existing suite pass; do not wait for another architecture decision.
