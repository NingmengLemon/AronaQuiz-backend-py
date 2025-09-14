from enum import StrEnum, auto
from uuid import UUID

from pydantic import BaseModel, Field

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


class UserResponse(BaseUser):
    id: UUID


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


class CreateProblemSetResponse(BaseModel):
    id: UUID
    status: ProblemSetCreateStatus
