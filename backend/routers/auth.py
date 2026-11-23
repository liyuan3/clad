"""POST /api/auth/login. Users are provisioned with the local CLI only; there is
no registration endpoint."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import AuthSession, User, utcnow
from ..schemas import LoginRequest, LoginResponse
from ..security import burn_password_check, new_token, token_hash, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID = "用户名或密码错误"


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> LoginResponse:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None:
        burn_password_check(payload.password)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_INVALID)
    if not verify_password(user.password_hash, payload.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_INVALID)

    token = new_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_hash(token),
            expires_at=utcnow() + timedelta(seconds=request.app.state.settings.session_ttl_seconds),
        )
    )
    db.commit()
    return LoginResponse(access_token=token, username=user.username)
