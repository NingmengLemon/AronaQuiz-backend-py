import uuid
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Awaitable, Generic, TypeVar

from sqlalchemy.ext.asyncio.session import AsyncAttrs as _AsyncAttrs
from sqlmodel import Field, Relationship, SQLModel

T = TypeVar("T")

__all__ = ["Option", "Problem", "ProblemType"]


class AsyncAttrs(_AsyncAttrs, Generic[T]):
    if TYPE_CHECKING:
        awaitable_attrs: T  # type: ignore


class ProblemType(StrEnum):
    single_select = auto()
    multi_select = auto()


class OptionAsyncAttrs:
    id: Awaitable[uuid.UUID]
    # problem: Awaitable["Problem"]
    order: Awaitable[int]
    content: Awaitable[str]


class Option(SQLModel, AsyncAttrs[OptionAsyncAttrs], table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    problem_id: uuid.UUID = Field(foreign_key="problem.id")
    # problem: "Problem" = Relationship(back_populates="options")
    order: int
    content: str
    is_correct: bool


class ProblemAsyncAttrs:
    id: Awaitable[uuid.UUID]
    content: Awaitable[str]
    options: Awaitable[list[Option]]
    answers: Awaitable[str]
    type: Awaitable[ProblemType]


class Problem(SQLModel, AsyncAttrs[ProblemAsyncAttrs], table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    content: str
    options: list[Option] = Relationship(
        back_populates="problem",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    type: ProblemType


TABLES = [
    SQLModel.metadata.tables[t.__tablename__]  # type: ignore
    for t in (Option, Problem)
]
