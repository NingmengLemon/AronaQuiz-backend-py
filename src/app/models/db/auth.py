from datetime import datetime, timedelta
from enum import StrEnum, auto
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field

from app.config import get_settings
from app.utils.misc import utcnow

from .base import BaseHasId


class LoginSessionStatus(StrEnum):
    ACTIVE = auto()  # session ok
    REVOKED = auto()  # operated by user themselves
    KICKED = auto()  # operated by security sys or admins
    EXPIRED = auto()  # also judged by <expires_at> field
    INVALID = auto()  # for other invalid conditions


class LoginSession(BaseHasId, table=True):
    __tablename__ = "login_session"

    access_token: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(foreign_key="user.id")

    expires_at: datetime = Field(
        default_factory=lambda: utcnow()
        + timedelta(days=get_settings().auth.access_token_lifetime_days),
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
        default_factory=lambda: utcnow()
        + timedelta(days=get_settings().auth.refresh_token_lifetime_days),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    # refresh token rotate 时, 更新当前 session 的 refresh_token_hash 和 refresh_token_expires_at
    # 定期移除过旧的过期的 session
