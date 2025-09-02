import uuid

from pydantic import BaseModel, Field

from ..db.models import ProblemType


class Option(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    content: str
    order: int
    is_correct: bool


class BaseProblem(BaseModel):
    content: str
    options: list[Option]
    type: ProblemType


class Problem(BaseProblem):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)


class Statistic(BaseModel):
    correct_count: int | None = None
    total_count: int | None = None


class ProblemWithStat(Problem, Statistic):
    pass


class BaseUser(BaseModel):
    username: str
    nickname: str


class User(BaseUser):
    id: uuid.UUID


class ProblemSet(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    count: int


class SingleUserStat(Statistic):
    problem_id: uuid.UUID


class UserStat(BaseUser):
    problems: list[SingleUserStat] = Field(default_factory=list)
