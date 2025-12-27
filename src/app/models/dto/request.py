from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.db.problem import ProblemType, SelectiveProblemDetails

from .base import BaseUser


class BaseProblem(BaseModel):
    content: str


class BaseProblemSet(BaseModel):
    name: str
    description: str = ""
    is_public: bool = False
    tags: list[str] = []


class SelectiveProblemSubmit(BaseProblem):
    type: Literal[ProblemType.SELECTIVE] = ProblemType.SELECTIVE
    details: SelectiveProblemDetails


type ProblemSubmit = SelectiveProblemSubmit  # |...


class ProblemSetSubmit(BaseProblemSet):
    pass


class UserRegisterSubmit(BaseUser):
    password: str


class LoginByUsernameSubmit(BaseModel):
    username: str
    password: str


class LoginByEmailSubmit(BaseModel):
    email: str
    password: str


class LoginByUserIdSubmit(BaseModel):
    user_id: UUID
    password: str


class RefreshTokenSubmit(BaseModel):
    refresh_token: UUID
