from collections.abc import Awaitable
from datetime import datetime
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Literal, TypedDict
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
PROBLEM_DETAIL_TYPE_ADAPTERS: dict[ProblemType, TypeAdapter[ProblemDetails]] = {
    problem_type: TypeAdapter(detail_model)
    for problem_type, detail_model in PROBLEM_DETAIL_TYPE_MAPPING.items()
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

    @field_validator("details", mode="after")
    @classmethod
    def _validate_details_by_type(
        cls, value: dict[str, Any], info: ValidationInfo
    ) -> ProblemDetails:
        problem_type: ProblemType | None = info.data.get("type")
        if not problem_type:
            raise ValueError("unable to determine problem type")
        adapter = PROBLEM_DETAIL_TYPE_ADAPTERS.get(problem_type)
        if not adapter:
            raise ValueError(f"unknown problem type: {problem_type}")
        value_validated = adapter.validate_python(value)

        # detail validations
        match problem_type:
            case ProblemType.SELECTIVE:
                if (
                    sum(
                        value_validated["options"][i]["is_correct"]
                        for i in range(len(value_validated["options"]))
                    )
                    == 0
                ):
                    raise ValueError("至少需要一个正确选项")
                elif (value_validated["type"] == "single") and (
                    sum(
                        value_validated["options"][i]["is_correct"]
                        for i in range(len(value_validated["options"]))
                    )
                    > 1
                ):
                    raise ValueError("单选题只能有一个正确选项")
                elif value_validated["type"] == "multiple" and all(
                    option["is_correct"] is False
                    for option in value_validated["options"]
                ):
                    raise ValueError("多选题至少需要一个正确选项")
                elif len(value_validated["options"]) < 2:
                    raise ValueError("选项数量不能少于两个")

        return value_validated


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
