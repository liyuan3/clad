"""Device pairing.

``POST /api/devices/pairing`` issues a short-lived single-use code for the
logged-in user; ``POST /api/runner/pair`` consumes it and returns the device
credential. M1 allows exactly one device per user.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import get_current_device, get_current_user, get_db
from ..models import Device, PairingCode, User, iso, utcnow
from ..schemas import DeviceOut, PairRequest, PairResponse, PairingResponse
from ..security import (
    new_pairing_code,
    new_token,
    normalize_pairing_code,
    token_hash,
)

router = APIRouter(tags=["devices"])

_CODE_INVALID = "配对码无效或已过期"
_ALREADY_BOUND = "该账号已绑定设备，M1 每个账号只支持一台设备"


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[DeviceOut]:
    devices = db.scalars(
        select(Device).where(Device.user_id == user.id).order_by(Device.created_at)
    ).all()
    return [DeviceOut(id=d.id, name=d.name, status=d.status) for d in devices]


@router.post("/devices/pairing", response_model=PairingResponse)
def create_pairing_code(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PairingResponse:
    # One live code per user: the previous unused code stops working immediately.
    db.execute(
        update(PairingCode)
        .where(PairingCode.user_id == user.id, PairingCode.used_at.is_(None))
        .values(used_at=utcnow())
    )
    code = new_pairing_code()
    expires_at = utcnow() + timedelta(seconds=request.app.state.settings.pairing_ttl_seconds)
    db.add(
        PairingCode(
            user_id=user.id, code_hash=token_hash(normalize_pairing_code(code) or code), expires_at=expires_at
        )
    )
    db.commit()
    return PairingResponse(code=code, expires_at=iso(expires_at))


@router.get("/runner/device", response_model=DeviceOut)
def runner_device(device: Device = Depends(get_current_device)) -> DeviceOut:
    """Device-credential self-check: lets the runner verify its token on startup.
    Additive to the contract (no contract endpoint covers this); does not change
    existing behaviour."""
    return DeviceOut(id=device.id, name=device.name, status=device.status)


@router.post("/runner/pair", response_model=PairResponse)
def pair_device(payload: PairRequest, db: Session = Depends(get_db)) -> PairResponse:
    normalized = normalize_pairing_code(payload.code)
    record = (
        db.scalar(
            select(PairingCode).where(PairingCode.code_hash == token_hash(normalized))
        )
        if normalized
        else None
    )
    now = utcnow()
    if record is None or record.used_at is not None or record.expires_at <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=_CODE_INVALID)

    if db.scalar(select(Device).where(Device.user_id == record.user_id)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_ALREADY_BOUND)

    token = new_token()
    device = Device(
        user_id=record.user_id,
        name=payload.name.strip(),
        status="offline",
        token_hash=token_hash(token),
    )
    db.add(device)
    record.used_at = now
    try:
        db.flush()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=_ALREADY_BOUND)
    return PairResponse(device_id=device.id, device_token=token)
