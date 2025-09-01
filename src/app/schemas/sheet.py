import uuid

from pydantic import BaseModel, Field

from ..db.models import ProblemType


class Option(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    content: str
    order: int
    is_correct: bool


class Problem(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    content: str
    options: list[Option]
    type: ProblemType
