# Collaboration rules
Codex owns frontend/ and architecture. Hermes owns backend/, runner/, tests/, requirements.txt and docs/HERMES_REPORT.md.
Do not change docs/CONTRACT.md without recording a proposal first. Do not edit the original clawproduct-hunt checkout.
Never commit credentials, .env, databases, user conversations, logs or VM images. No production deployment.
Use separate branches/worktrees. Hermes commits only its owned files; Codex reviews before merge. Do not force push.
Implement real behavior; clearly distinguish mock tests from Windows/Claude integration verification.
