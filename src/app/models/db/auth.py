from datetime import datetime, timedelta
from enum import StrEnum, auto
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field

from app.utils.misc import utcnow
from app.utils.uuid7 import uuid7

from .base import Base

# TODO: make these configurable
ACCESS_TOKEN_LIFETIME = 14  # days
REFRESH_TOKEN_LIFETIME = 120  # days


class LoginSessionStatus(StrEnum):
    ACTIVE = auto()  # session ok
    REVOKED = auto()  # operated by user themselves
    KICKED = auto()  # operated by security sys or admins
    EXPIRED = auto()  # also judged by <expires_at> field
    INVALID = auto()  # for other invalid conditions


class LoginSession(Base, table=True):
    __tablename__ = "login_session"
    id: UUID = Field(default_factory=uuid7, primary_key=True)

    access_token: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(foreign_key="user.id")

    expires_at: datetime = Field(
        default_factory=lambda: utcnow() + timedelta(days=ACCESS_TOKEN_LIFETIME),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_renewal: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_active: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    status: LoginSessionStatus = LoginSessionStatus.ACTIVE

    device_info: str = ""
    refresh_token_hash: str
    refresh_token_expires_at: datetime = Field(
        default_factory=lambda: utcnow() + timedelta(days=REFRESH_TOKEN_LIFETIME),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    # refresh token rotate 时, 创建一个新的 session, 将当前 session 设为 expired
    # 定期移除过旧的过期的 session
