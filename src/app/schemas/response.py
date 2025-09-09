import uuid
from enum import StrEnum, auto

from pydantic import BaseModel, Field

from ._base import (
    BaseOption,
    BaseProblem,
    BaseProblemSet,
    BaseStatistic,
    BaseUser,
)


class OptionResponse(BaseOption):
    id: uuid.UUID


class ProblemResponse(BaseProblem, BaseStatistic):
    id: uuid.UUID
    options: list[OptionResponse]


class UserResponse(BaseUser):
    id: uuid.UUID


class ProblemSetResponse(BaseProblemSet):
    count: int
    id: uuid.UUID


class SingleUserStatResponse(BaseStatistic):
    problem_id: uuid.UUID
    user_id: uuid.UUID


class UserStatResponse(BaseUser):
    problems: list[SingleUserStatResponse] = Field(default_factory=list)


class ProblemSetCreateStatus(StrEnum):
    success = auto()
    already_exists = auto()


class CreateProblemSetResponse(BaseModel):
    id: uuid.UUID
    status: ProblemSetCreateStatus
