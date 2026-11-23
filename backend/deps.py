"""Request dependencies: DB session, user token auth, device token auth."""

from __future__ import annotations

from typing import Iterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuthSession, Device, User, utcnow
from .security import token_hash

bearer_scheme = HTTPBearer(auto_error=False)


def get_db(request: Request) -> Iterator[Session]:
    """Request-scoped session. Handlers that write call ``db.commit()`` themselves:
    FastAPI runs dependency teardown *after* the response is sent, so committing
    only there would let a follow-up request read stale data."""
    session = request.app.state.db.new_session()
    try:
        yield session
    finally:
        session.close()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("未登录")
    record = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == token_hash(credentials.credentials))
    )
    if record is None:
        raise _unauthorized("登录已失效，请重新登录")
    if record.expires_at <= utcnow():
        db.delete(record)
        db.commit()
        raise _unauthorized("登录已过期，请重新登录")
    user = db.get(User, record.user_id)
    if user is None:
        raise _unauthorized("登录已失效，请重新登录")
    return user


def get_current_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Device:
    """Device credential check, used by the runner endpoints (pairing today,
    websocket/artifacts in the next batch)."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("设备未认证")
    device = db.scalar(
        select(Device).where(Device.token_hash == token_hash(credentials.credentials))
    )
    if device is None:
        raise _unauthorized("设备凭据无效")
    return device
