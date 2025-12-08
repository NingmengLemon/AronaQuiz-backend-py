from enum import StrEnum, auto
from uuid import UUID

from pydantic import EmailStr
from sqlmodel import Field
from app.utils.uuid7 import uuid7

from .base import Base


class UserRole(StrEnum):
    USER = auto()  # permission level: min
    ADMIN = auto()
    SU = auto()  # permission level: max


class DBUser(Base, table=True):
    __tablename__ = "user"
    # 所有属性都无需二次 await 所以没写
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    email: EmailStr = Field(unique=True)
    username: str = Field(unique=True)
    password_hash: str
    nickname: str = Field(unique=True)
    role: UserRole = UserRole.USER
