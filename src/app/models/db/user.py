from enum import StrEnum, auto

from pydantic import EmailStr
from sqlmodel import Field

from .base import BaseHasId


class UserRole(StrEnum):
    USER = auto()  # permission level: min
    ADMIN = auto()
    SU = auto()  # permission level: max


class DBUser(BaseHasId, table=True):
    __tablename__ = "user"
    # 所有属性都无需二次 await 所以没写 AsyncAttrs
    email: EmailStr = Field(unique=True)
    username: str = Field(unique=True)
    password_hash: str
    nickname: str = Field(unique=True)
    role: UserRole = UserRole.USER
