import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.stat import DBAnswerRecord
from app.utils.db import in_transaction
from app.utils.misc import utcnow

logger = logging.getLogger("uvicorn.error")


@in_transaction()
async def report_attempt(
    session: AsyncSession,
    problem_id: UUID,
    user_id: UUID,
    correct: bool,
    time: datetime | None = None,
) -> None:
    if (
        record := (
            await session.exec(
                select(DBAnswerRecord).where(
                    DBAnswerRecord.user_id == user_id,
                    DBAnswerRecord.problem_id == problem_id,
                )
            )
        ).one_or_none()
    ) is None:
        record = DBAnswerRecord(user_id=user_id, problem_id=problem_id)

    record.total_count += 1
    if correct:
        record.correct_count += 1
    record.last_attempt = time or utcnow()
    session.add(record)
    await session.flush()


async def query_statistic(
    session: AsyncSession,
    *,
    problem_id: UUID | None = None,
    user_id: UUID | None = None,
) -> Any:
    raise NotImplementedError
