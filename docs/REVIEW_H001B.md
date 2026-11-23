# H001b Codex review — changes requested
Reviewed e61f4dd on 2026-11-23. Do not merge to main yet.
Independent baseline: 93 pytest passed; 21 real-process websocket/restart checks passed.
Two additional regressions in docs/h001b_review_regressions.py both fail on this commit. Copy into tests/ for execution after syncing main.

## R1 / blocking: unknown can bypass reconciliation
backend/routers/runner.py accepts done on unknown without last_seq; report requires matching last_seq but done bypasses it. Reconnect then done completes run and releases device without proving output replay is complete. Reject done on unknown; require verified report (or a unified finalization protocol with mandatory final seq). A rejected/missing event followed by done must never silently truncate output. Add regression with pending/unacked final chunks, not just a normal reconnect.

## R2 / blocking: uncertain send is not proof of non-delivery
hub.send returns False for both no connection and send exception. runs.py marks both dispatch_failed=True. apply_report(not_found) then releases unknown run without checking last_seq or any existing events. Reproduced: send delivered but returns False; runner sends text seq=1; then not_found,last_seq=0 still resolves failed and frees device.
Separate proven-not-attempted from uncertain transport failure, or conservatively never auto-release not_found in M1. Existing execution events always forbid not_found; validate last_seq for every report. Document the exact evidence required, and test the send-after-delivery failure boundary.

## R3 / required compatibility: preserve H001a databases
Do not instruct deletion of a working user/device/conversation database. Add explicit versioned/idempotent upgrade (CLI command acceptable) for new nullable columns, tables and indexes. Verify H001a data survives upgrade and paired credentials still work; rerunning migration is safe. Refuse unsupported schema with backup/upgrade instructions, not deletion. Migration must run before schema-dependent create_all/index work.

## Follow-ups in this correction batch
- write_assistant_message catches every exception and rolls back the entire transaction then finish_run reports success. Do not swallow unexpected storage errors or emit successful ACK after rollback. Keep final state + message atomic; test injected DB failure.
- Fence inbound writes by current connection_id, not only cleanup. Replaced sockets must not publish events/done/report/heartbeat after takeover.
- Ensure runner register/connected send failures are covered by finally cleanup.
- Persist and resend pending cancellation on reconnect with idempotent runner handling; do not claim cancel confirmation until acknowledged.
- Add bounded per-event payload size and rejection before persistence.

Do NOT add Claude integration/artifact upload yet. Keep frontend untouched. Commit fixes on hermes/backend-m1, preserve existing report and append correction results to docs/HERMES_REPORT_H001B.md. Codex will re-review.
