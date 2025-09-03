import uuid
from enum import StrEnum, auto

from pydantic import BaseModel, Field

from ..db.models import ProblemType


class _BaseOption(BaseModel):
    content: str
    order: int
    is_correct: bool


class OptionSubmit(_BaseOption):
    pass


class OptionResponse(_BaseOption):
    id: uuid.UUID


class _BaseProblem(BaseModel):
    content: str
    type: ProblemType


class ProblemSubmit(_BaseProblem):
    options: list[OptionSubmit]


class _BaseStatistic(BaseModel):
    correct_count: int = 0
    total_count: int = 0


class DeleteProblemSubmit(BaseModel):
    ids: list[uuid.UUID]


class ProblemResponse(_BaseProblem, _BaseStatistic):
    id: uuid.UUID
    options: list[OptionResponse]


class _BaseUser(BaseModel):
    username: str
    nickname: str


class UserResponse(_BaseUser):
    id: uuid.UUID


class _BaseProblemSet(BaseModel):
    name: str


class ProblemSetSubmit(_BaseProblemSet):
    pass


class ProblemSetResponse(_BaseProblemSet):
    count: int
    id: uuid.UUID


class SingleUserStatResponse(_BaseStatistic):
    problem_id: uuid.UUID
    user_id: uuid.UUID


class UserStatResponse(_BaseUser):
    problems: list[SingleUserStatResponse] = Field(default_factory=list)


class ProblemSetCreateStatus(StrEnum):
    success = auto()
    already_exists = auto()


class CreateProblemSetResponse(BaseModel):
    id: uuid.UUID
    status: ProblemSetCreateStatus
