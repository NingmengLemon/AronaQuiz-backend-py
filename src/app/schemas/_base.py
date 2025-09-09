from pydantic import BaseModel

from app.db.models import ProblemType


class BaseOption(BaseModel):
    content: str
    order: int
    is_correct: bool


class BaseProblem(BaseModel):
    content: str
    type: ProblemType


class BaseStatistic(BaseModel):
    correct_count: int = 0
    total_count: int = 0


class BaseUser(BaseModel):
    username: str
    nickname: str


class BaseProblemSet(BaseModel):
    name: str
