"""Request/response models. Field limits are part of the API surface."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    access_token: str
    username: str


class PairingResponse(BaseModel):
    code: str
    expires_at: str


class PairRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=64)


class PairResponse(BaseModel):
    device_id: str
    device_token: str


class DeviceOut(BaseModel):
    id: str
    name: str
    status: str


class ConversationCreate(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)


class ConversationOut(BaseModel):
    id: str
    title: str
    device_id: str
    created_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
