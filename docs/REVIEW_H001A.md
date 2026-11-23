# H001a Codex review
2026-11-23: accepted for development baseline, not production release.
Reviewed commit 75a87b9: scope matches H001a; frontend and contract unchanged.
Independently executed 42 pytest tests: passed (one Starlette/httpx deprecation warning).
Independently executed tests/smoke_live.py against a new uvicorn process, isolated temporary SQLite database and real frontend: all 18 checks passed. Test process stopped afterwards.
Reviewed ownership checks, token type separation, hashed credentials, device uniqueness and explicit write commits. No blocking finding in this scope.
Accept GET /api/health and GET /api/runner/device as additive contract endpoints.
Browser appearance reported by Hermes, not independently reverified by Codex in this review. No Windows or Claude execution verified.
Follow-ups: reject whitespace-only device names; smoke script currently requires a fresh database (document or randomize fixture usernames); login/pair throttling before public deployment. Rate limiting is not provided by password hashing.
