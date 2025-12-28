from collections.abc import Awaitable
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Uuid
from sqlmodel import Field, Relationship

from app.utils.db import datetime_column_tzaware
from app.utils.misc import utcnow

from .base import AsyncAttrs, Base, BaseHasId

if TYPE_CHECKING:
    from .problem import DBProblem, DBProblemSet


class ProblemTagLink(Base, table=True):
    __tablename__ = "problem_tag_link"
    problem_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid,
            ForeignKey("problem.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    tag_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid,
            ForeignKey("tag.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


class ProblemSetTagLink(Base, table=True):
    __tablename__ = "problemset_tag_link"
    problemset_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid,
            ForeignKey("problemset.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    tag_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid,
            ForeignKey("tag.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


class _TagAsyncAttrs:
    problems: Awaitable[list["DBProblem"]]
    problemsets: Awaitable[list["DBProblemSet"]]


class DBTag(BaseHasId, AsyncAttrs[_TagAsyncAttrs], table=True):
    __tablename__ = "tag"
    name: str = Field(unique=True, index=True, max_length=100)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=datetime_column_tzaware(),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=datetime_column_tzaware(onupdate=utcnow),
    )

    problems: list["DBProblem"] = Relationship(
        back_populates="tags", link_model=ProblemTagLink
    )
    problemsets: list["DBProblemSet"] = Relationship(
        back_populates="tags", link_model=ProblemSetTagLink
    )
