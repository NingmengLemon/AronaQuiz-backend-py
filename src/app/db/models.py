import datetime
import uuid
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Awaitable, Generic, TypeVar

from sqlalchemy.ext.asyncio.session import AsyncAttrs as _AsyncAttrs
from sqlmodel import Field, Relationship, SQLModel

T = TypeVar("T")

__all__ = ["DBOption", "DBProblem", "ProblemType"]


class AsyncAttrs(_AsyncAttrs, Generic[T]):
    if TYPE_CHECKING:
        awaitable_attrs: T  # type: ignore


class ProblemType(StrEnum):
    single_select = auto()
    multi_select = auto()


class OptionAsyncAttrs:
    problem: Awaitable["DBProblem"]


class DBOption(SQLModel, AsyncAttrs[OptionAsyncAttrs], table=True):
    __tablename__ = "option"  # type: ignore
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order: int
    content: str
    is_correct: bool

    problem_id: uuid.UUID = Field(
        foreign_key="problem.id",
        # sa_column_kwargs={"ondelete": "CASCADE"},
    )
    problem: "DBProblem" = Relationship(back_populates="options")


class ProblemAsyncAttrs:
    options: Awaitable[list[DBOption]]
    problemset: Awaitable["DBProblemSet"]


class DBProblem(SQLModel, AsyncAttrs[ProblemAsyncAttrs], table=True):
    __tablename__ = "problem"  # type: ignore
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    content: str
    type: ProblemType

    problemset_id: uuid.UUID = Field(foreign_key="problemset.id")
    problemset: "DBProblemSet" = Relationship(back_populates="problems")
    options: list[DBOption] = Relationship(
        back_populates="problem",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class ProblemSetAsyncAttrs:
    problems: Awaitable[list[DBProblem]]


class DBProblemSet(SQLModel, AsyncAttrs[ProblemSetAsyncAttrs], table=True):
    __tablename__ = "problemset"  # type: ignore
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str

    problems: list[DBProblem] = Relationship(
        back_populates="problemset",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class DBUser(SQLModel, AsyncAttrs, table=True):
    __tablename__ = "user"  # type: ignore
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(unique=True)
    password_hash: str | None = None
    password_salt: str | None = None
    nickname: str | None = None


class DBAnswerRecord(SQLModel, AsyncAttrs, table=True):
    __tablename__ = "answerrecord"  # type: ignore
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    problem_id: uuid.UUID = Field(foreign_key="problem.id", index=True)

    correct_count: int = 0
    total_count: int = 0
    last_attempt: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.fromtimestamp(0)
    )


TABLES = [
    SQLModel.metadata.tables[t.__tablename__]  # type: ignore
    for t in (
        DBOption,
        DBProblem,
        DBProblemSet,
        DBUser,
        DBAnswerRecord,
    )
]
