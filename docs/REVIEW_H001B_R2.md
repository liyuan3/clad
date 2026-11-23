# H001b second review — e4a1025
Changes requested. Independent baseline: 111 pytest and 23 live checks passed. Two additional tests in docs/h001b_rereview_regressions.py fail. Do not merge implementation yet.

## R2 remains: DELIVERED and NOT_CONNECTED collapse to the same stored value
Run.dispatch_uncertain defaults False; record_dispatch_result returns immediately for DELIVERED, also leaving False. apply_report treats False as proof of NOT_CONNECTED. Reproduced: runner receives run, disconnects before emitting any event, reconnects and reports not_found/0; server incorrectly releases device.
Store an explicit durable dispatch outcome (NOT_ATTEMPTED, NOT_CONNECTED, DELIVERED, UNCERTAIN or equivalent). Only a persisted, proven NOT_CONNECTED result may authorize not_found; creation/crash windows and all legacy rows default conservatively to uncertain. A successful websocket write is NOT proof of no execution. Test successful delivery with zero events; process crash before recording send result; upgrade of existing H001b rows. Do not simply invert the old boolean because its historical semantics changed.

## R1 remains: stream_error clears before the rejected suffix is repaired
Reproduced seq1 accepted -> seq3 rejected -> seq2 accepted -> done(last_seq=2) succeeds, losing seq3. Existing test_rejected_event_blocks_done_until_repaired actually asserts this truncated result is correct; fix the assertion instead of retaining it.
Persist a required recovery boundary / unresolved rejection state, not a boolean cleared by any accepted event. Completion and report require all required events repaired. At minimum track the highest rejected valid sequence for gaps/oversize, and do not let a later unrelated event clear a conflict at an already stored sequence. Conflicting replay must be resolved by replay of the canonical stored content, or remain conservatively blocked under a documented protocol. Test both done and report, restart while repair is pending, and full seq3 repair resulting in all three text chunks exactly once. Retain event size bounds.

## Migration preflight (small but necessary)
upgrade currently only recognizes users/devices/messages table names and checks user_version after mutating. Reject future schema versions and unrecognized/incomplete column layouts BEFORE any DDL. Test a future version and malformed lookalike schema remain unchanged. Preserve legitimate H001a upgrade and repeatability.

Scope remains correction only, no Claude or artifacts. Keep frontend unchanged. Merge latest main to obtain these reproduction tests, add them to tests/, implement corrections, run full suite/live checks, append report and commit locally for Codex review.
