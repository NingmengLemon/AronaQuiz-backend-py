from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import Column, DateTime, PrimaryKeyConstraint
from sqlmodel import Field

from .base import Base


class DBAnswerRecord(Base, table=True):
    __tablename__ = "answer_record"
    __table_args__ = (PrimaryKeyConstraint("user_id", "problem_id"),)
    user_id: UUID = Field(foreign_key="user.id")
    problem_id: UUID = Field(foreign_key="problem.id")

    correct_count: int = 0
    total_count: int = 0
    last_attempt: datetime = Field(
        default_factory=lambda: datetime.fromtimestamp(0, timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
