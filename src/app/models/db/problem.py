from collections.abc import Awaitable
from enum import StrEnum, auto
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Uuid
from sqlmodel import Field, Relationship

from app.utils.uuid7 import uuid7

from .base import AsyncAttrs, Base


class ProblemType(StrEnum):
    single_select = auto()
    multi_select = auto()


class _OptionAsyncAttrs:
    problem: Awaitable["DBProblem"]


class DBOption(Base, AsyncAttrs[_OptionAsyncAttrs], table=True):
    __tablename__ = "option"
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    order: int
    content: str
    is_correct: bool

    problem_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("problem.id", ondelete="CASCADE"))
    )
    problem: "DBProblem" = Relationship(back_populates="options")


class _ProblemAsyncAttrs:
    options: Awaitable[list[DBOption]]
    problemset: Awaitable["DBProblemSet"]


class DBProblem(Base, AsyncAttrs[_ProblemAsyncAttrs], table=True):
    __tablename__ = "problem"
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    content: str
    type: ProblemType

    problemset_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("problemset.id", ondelete="CASCADE"))
    )
    problemset: "DBProblemSet" = Relationship(back_populates="problems")
    options: list[DBOption] = Relationship(
        back_populates="problem",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class _ProblemSetAsyncAttrs:
    problems: Awaitable[list[DBProblem]]


class DBProblemSet(Base, AsyncAttrs[_ProblemSetAsyncAttrs], table=True):
    __tablename__ = "problemset"
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    name: str

    problems: list[DBProblem] = Relationship(
        back_populates="problemset",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
