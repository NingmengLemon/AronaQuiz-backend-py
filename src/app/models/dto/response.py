from enum import StrEnum, auto
from uuid import UUID

from pydantic import BaseModel

from app.models.db.problem import ProblemDetails, ProblemType
from app.models.db.user import UserRole

from .base import BaseUser


class ProblemResponse(BaseModel):
    id: UUID
    type: ProblemType
    content: str
    explanation: str | None
    details: ProblemDetails


class UserInfoResponse(BaseUser):
    id: UUID


class SelfInfoResponse(UserInfoResponse):
    role: UserRole


class ProblemSetResponse(BaseModel):
    id: UUID
    name: str
    count: int


class ProblemSetCreateStatus(StrEnum):
    SUCCESS = auto()
    ALREADY_EXISTS = auto()


class ProblemSetCreateResponse(BaseModel):
    id: UUID
    status: ProblemSetCreateStatus


class UserCreateResponse(SelfInfoResponse):
    pass


class RefreshTokenResponse(BaseModel):
    access_token: UUID
    refresh_token: UUID | None = None


class LoginSuccessResponse(BaseModel):
    access_token: UUID
    refresh_token: UUID
