from enum import StrEnum, auto
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import UserRole

from ._base import (
    BaseOption,
    BaseProblem,
    BaseProblemSet,
    BaseStatistic,
    BaseUser,
)


class OptionResponse(BaseOption):
    id: UUID


class ProblemResponse(BaseProblem):
    id: UUID
    options: list[OptionResponse]


class UserInfoResponse(BaseUser):
    id: UUID


class SelfInfoResponse(UserInfoResponse):
    role: UserRole


class ProblemSetResponse(BaseProblemSet):
    count: int
    id: UUID


class SingleUserStatResponse(BaseStatistic):
    problem_id: UUID
    user_id: UUID


class UserStatResponse(BaseUser):
    problems: list[SingleUserStatResponse] = Field(default_factory=list)


class ProblemSetCreateStatus(StrEnum):
    success = auto()
    already_exists = auto()


class ProblemSetCreateResponse(BaseModel):
    id: UUID
    status: ProblemSetCreateStatus


class UserCreateResponse(BaseModel):
    user_id: UUID
