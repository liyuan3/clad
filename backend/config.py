"""Runtime settings. Everything is overridable by environment variables so no
worktree path is hard-coded at call sites."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:  # fail loudly: a bad value must not silently change TTLs
        raise RuntimeError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive, got {value}")
    return value


def _default_database_url() -> str:
    path = REPO_ROOT / "data" / "clad.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


@dataclass(frozen=True)
class Settings:
    database_url: str
    frontend_dir: Path
    session_ttl_seconds: int = 7 * 24 * 3600
    pairing_ttl_seconds: int = 10 * 60

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get("CLAD_DATABASE_URL") or _default_database_url(),
            frontend_dir=Path(
                os.environ.get("CLAD_FRONTEND_DIR") or (REPO_ROOT / "frontend")
            ).expanduser(),
            session_ttl_seconds=_int_env("CLAD_SESSION_TTL_SECONDS", 7 * 24 * 3600),
            pairing_ttl_seconds=_int_env("CLAD_PAIRING_TTL_SECONDS", 10 * 60),
        )
