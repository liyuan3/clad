# Hermes task H001
Read AGENTS.md and docs/CONTRACT.md. Implement backend and runner for contract. Use FastAPI, SQLAlchemy/SQLite and Python runner. Read original project selectively; reuse safe concepts rather than copying all marketplace code.
1. Implement authentication, device pairing/ownership, conversations and persistent run/event state.
2. Implement outbound runner websocket protocol, duplicate handling and reconnect reconciliation.
3. Implement Claude adapter, durable session mapping and execution journal, cancellation and artifacts. Include a fake adapter for automated tests only.
4. Tests must cover cross-user denial, pairing expiration/reuse, busy/offline rejection, request dedupe, event replay, server restart reconciliation and cancellation.
5. Provide setup/user provisioning/runner Windows startup commands and exact dependencies.
6. Report tests, limits and contract deviations in docs/HERMES_REPORT.md. Do not claim Windows live validation from Linux mocks.
Commit on hermes/backend-m1; push that branch if credentials work. Do not merge main, edit frontend, deploy, or modify original repo. Work only in /home/fo/clad-hermes. If blocked, write precise report and stop; never print credentials. Prioritize working tested backend first over broad incomplete features.
