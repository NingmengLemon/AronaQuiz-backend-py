from collections.abc import Awaitable
from datetime import datetime
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Literal, Type, TypedDict
from uuid import UUID

from pydantic import (
    TypeAdapter,
    ValidationInfo,
    field_validator,
)
from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from app.utils.db import datetime_column_tzaware
from app.utils.misc import utcnow

from .base import AsyncAttrs, BaseHasId
from .tag import ProblemSetTagLink, ProblemTagLink

if TYPE_CHECKING:
    from .tag import DBTag
    from .user import DBUser


class ProblemType(StrEnum):
    SELECTIVE = auto()


class SelectiveProblemOption(TypedDict):
    order: int
    is_correct: bool
    content: str


class SelectiveProblemDetails(TypedDict):
    type: Literal["single", "multiple"]
    options: list[SelectiveProblemOption]


type ProblemDetails = SelectiveProblemDetails  # | ...


class _ProblemAsyncAttrs:
    problemset: Awaitable["DBProblemSet"]
    tags: Awaitable[list["DBTag"]]


PROBLEM_DETAIL_TYPE_MAPPING: dict[ProblemType, type[ProblemDetails]] = {
    ProblemType.SELECTIVE: SelectiveProblemDetails,
}


class DBProblem(BaseHasId, AsyncAttrs[_ProblemAsyncAttrs], table=True):
    __tablename__ = "problem"
    type: ProblemType
    content: str
    details: ProblemDetails = Field(sa_column=Column(JSONB, nullable=False))
    explanation: str | None = None

    problemset_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("problemset.id", ondelete="CASCADE"))
    )
    problemset: "DBProblemSet" = Relationship(back_populates="problems")
    tags: list["DBTag"] = Relationship(
        back_populates="problems", link_model=ProblemTagLink
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=datetime_column_tzaware(),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=datetime_column_tzaware(onupdate=utcnow),
    )

    __table_args__ = (
        Index("ix_problem_details_gin", "details", postgresql_using="gin"),
    )

    @staticmethod
    def problem_type_to_detail_model(
        problem_type: ProblemType,
    ) -> Type[ProblemDetails]:
        detail_model = PROBLEM_DETAIL_TYPE_MAPPING.get(problem_type)
        if not detail_model:
            raise ValueError(f"unknown problem type: {problem_type}")
        return detail_model

    @field_validator("details", mode="after")
    @classmethod
    def _validate_details_by_type(
        cls, value: dict[str, Any], info: ValidationInfo
    ) -> ProblemDetails:
        problem_type: ProblemType | None = info.data.get("type")
        if not problem_type:
            raise ValueError("unable to determine problem type")
        detail_model = cls.problem_type_to_detail_model(problem_type)
        adapter = TypeAdapter(detail_model)
        return adapter.validate_python(value)


class _ProblemSetAsyncAttrs:
    problems: Awaitable[list[DBProblem]]
    owner: Awaitable["DBUser"]
    tags: Awaitable[list["DBTag"]]


class DBProblemSet(BaseHasId, AsyncAttrs[_ProblemSetAsyncAttrs], table=True):
    __tablename__ = "problemset"
    name: str
    description: str = Field(default="")
    is_public: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=datetime_column_tzaware(),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=datetime_column_tzaware(onupdate=utcnow),
    )

    owner_id: UUID = Field(sa_column=Column(Uuid, ForeignKey("user.id")))
    owner: "DBUser" = Relationship(back_populates="problemsets")

    problems: list[DBProblem] = Relationship(
        back_populates="problemset",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    tags: list["DBTag"] = Relationship(
        back_populates="problemsets", link_model=ProblemSetTagLink
    )

    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_problemset_owner_id_name"),
    )
