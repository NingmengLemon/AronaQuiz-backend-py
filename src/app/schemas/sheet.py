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


class ProblemSet(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    count: int
