"""Conversation list/create and message history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Conversation, Device, Message, User, iso
from ..schemas import ConversationCreate, ConversationOut, MessageOut

router = APIRouter(prefix="/conversations", tags=["conversations"])

_NOT_FOUND = "会话不存在"
_DEVICE_NOT_FOUND = "设备不存在"


def _owned_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    # Same answer for "missing" and "someone else's": do not leak existence.
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return conversation


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ConversationOut]:
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    ).all()
    return [
        ConversationOut(
            id=c.id, title=c.title, device_id=c.device_id, created_at=iso(c.created_at)
        )
        for c in rows
    ]


@router.post("", response_model=ConversationOut)
def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationOut:
    device = db.get(Device, payload.device_id)
    if device is None or device.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_DEVICE_NOT_FOUND)

    title = payload.title.strip()
    if not title:
        raise HTTPException(422, detail="标题不能为空")

    conversation = Conversation(user_id=user.id, device_id=device.id, title=title)
    db.add(conversation)
    db.flush()
    db.commit()
    return ConversationOut(
        id=conversation.id,
        title=conversation.title,
        device_id=conversation.device_id,
        created_at=iso(conversation.created_at),
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MessageOut]:
    _owned_conversation(db, user, conversation_id)
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
    ).all()
    return [
        MessageOut(
            id=m.id, role=m.role, content=m.content, created_at=iso(m.created_at)
        )
        for m in rows
    ]
