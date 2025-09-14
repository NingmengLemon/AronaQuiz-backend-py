import datetime
import logging
from typing import Any, cast, overload
from uuid import UUID

from sqlalchemy.orm import QueryableAttribute, selectinload
from sqlmodel import col, delete, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.decos import in_transaction
from app.schemas.request import ProblemSubmit
from app.schemas.response import (
    ProblemResponse,
    ProblemSetCreateStatus,
    ProblemSetResponse,
)
from app.typ import T

from .models import DBAnswerRecord, DBOption, DBProblem, DBProblemSet, DBUser

logger = logging.getLogger("uvicorn.error")


def queryable(o: T) -> QueryableAttribute[T]:
    return cast(QueryableAttribute, o)


@in_transaction()
async def create_problemset(
    session: AsyncSession, name: str
) -> tuple[UUID, ProblemSetCreateStatus]:
    name = name.strip()
    problemset = (
        await session.exec(select(DBProblemSet).where(DBProblemSet.name == name))
    ).one_or_none()
    if problemset is not None:
        return problemset.id, ProblemSetCreateStatus.already_exists
    problemset = DBProblemSet(name=name, problems=[])
    session.add(problemset)

    return problemset.id, ProblemSetCreateStatus.success


@in_transaction()
async def add_problems(
    session: AsyncSession, problemset_id: UUID, *problems: ProblemSubmit
) -> list[UUID] | None:
    problemset = (
        await session.exec(select(DBProblemSet).where(DBProblemSet.id == problemset_id))
    ).one_or_none()
    if problemset is None:
        return None
    added_ids: list[UUID] = []
    for problem in problems:
        problem_db = DBProblem.model_validate(
            problem,
            update={
                "options": [],
                "problemset_id": problemset.id,
                "problemset": problemset,
            },
        )
        problem_id = problem_db.id
        options_db = [
            DBOption.model_validate(o, update={"problem_id": problem_db.id})
            for o in problem.options
        ]
        problem_db.options = options_db
        session.add_all([problem_db, *options_db])
        added_ids.append(problem_id)

    return added_ids


async def query_problem(
    session: AsyncSession, problem_id: UUID
) -> ProblemResponse | None:
    """not public"""
    problem_db = (
        await session.exec(
            select(DBProblem)
            .where(DBProblem.id == problem_id)
            .options(selectinload(queryable(DBProblem.options)))
        )
    ).one_or_none()
    return (
        ProblemResponse.model_validate(problem_db, from_attributes=True)
        if problem_db is not None
        else None
    )


async def search_problem(
    session: AsyncSession,
    kw: str | None = None,
    problemset_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[ProblemResponse]:
    stmt = select(DBProblem)
    if problemset_id:
        stmt = stmt.where(DBProblem.problemset_id == problemset_id)
    if kw:
        stmt = (
            stmt.outerjoin(DBOption)
            .filter(
                or_(
                    col(DBProblem.content).icontains(kw),
                    col(DBOption.content).icontains(kw),
                )
            )
            .distinct()
        )
    stmt = stmt.offset(page_size * (page - 1)).limit(page_size)
    db_problems = (
        await session.exec(stmt.options(selectinload(queryable(DBProblem.options))))
    ).all()
    result: list[ProblemResponse] = []
    for p in db_problems:
        result.append(ProblemResponse.model_validate(p, from_attributes=True))

    return result


@in_transaction()
async def delete_problems(
    session: AsyncSession,
    *problem_ids: UUID,
) -> None:
    stmt = delete(DBProblem)
    stmt = stmt.where(col(DBProblem.id).in_(problem_ids))
    await session.exec(stmt)  # type: ignore
    stmt = delete(DBOption)
    stmt = stmt.where(col(DBOption.problem_id).in_(problem_ids))
    await session.exec(stmt)  # type: ignore


@in_transaction()
async def delete_problemset(session: AsyncSession, problemset_id: UUID) -> None | UUID:
    problemset = (
        await session.exec(select(DBProblemSet).where(DBProblemSet.id == problemset_id))
    ).one_or_none()
    if not problemset:
        return None
    await session.delete(problemset)
    await session.exec(
        delete(DBProblem).where(col(DBProblem.problemset_id) == problemset_id)  # type: ignore
    )
    return problemset_id


async def get_problem_count(
    session: AsyncSession, problemset_id: UUID | None = None
) -> int:
    stmt = select(func.count())
    if problemset_id:
        stmt = stmt.where(DBProblem.problemset_id == problemset_id)
    return (await session.exec(stmt.select_from(DBProblem))).one()


async def sample(
    session: AsyncSession, problemset_id: UUID, n: int = 20
) -> list[ProblemSubmit]:
    db_problems = await session.exec(
        select(DBProblem)
        .where(DBProblem.problemset_id == problemset_id)
        .order_by(func.random())
        .limit(n)
        .options(selectinload(queryable(DBProblem.options)))
    )
    return [ProblemSubmit.model_validate(p, from_attributes=True) for p in db_problems]


async def list_problemset(session: AsyncSession) -> list[ProblemSetResponse]:
    dbproblemsets = (await session.exec(select(DBProblemSet))).all()
    return [
        ProblemSetResponse(id=ps.id, name=ps.name, count=cnt)
        for ps, cnt in zip(
            dbproblemsets,
            [
                (await get_problem_count(session, problemset_id=ps_.id))
                for ps_ in dbproblemsets
            ],
        )
    ]


@in_transaction()
async def delete_all(session: AsyncSession) -> None:
    # 加 type: ignore 的原因是:
    # https://github.com/fastapi/sqlmodel/issues/909
    await session.exec(delete(DBProblemSet))  # type: ignore
    await session.exec(delete(DBProblem))  # type: ignore
    await session.exec(delete(DBOption))  # type: ignore


@overload
async def query_user(session: AsyncSession, *, username: str) -> DBUser | None: ...


@overload
async def query_user(session: AsyncSession, *, user_id: UUID) -> DBUser | None: ...


async def query_user(
    session: AsyncSession,
    *,
    username: str | None = None,
    user_id: UUID | None = None,
) -> DBUser | None:
    if not ((username is None) ^ (user_id is None)):
        raise ValueError("choose from username and user_id")
    return (
        await session.exec(
            select(DBUser).where(
                DBUser.username == username if username else DBUser.id == user_id
            )
        )
    ).one_or_none()


@in_transaction()
async def create_user(session: AsyncSession, username: str) -> DBUser:
    raise NotImplementedError


@in_transaction()
async def create_record(
    session: AsyncSession, user_id: UUID, problem_id: UUID
) -> DBAnswerRecord:
    record = DBAnswerRecord(user_id=user_id, problem_id=problem_id)
    session.add(record)
    return record


async def ensure_record(
    session: AsyncSession, user_id: UUID, problem_id: UUID
) -> DBAnswerRecord:
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
        record = await create_record(
            session,
            user_id,
            problem_id,
        )
    return record


@in_transaction()
async def report_attempt(
    session: AsyncSession,
    problem_id: UUID,
    user_id: UUID,
    correct: bool,
    time: datetime.datetime | None = None,
) -> None:
    record = await ensure_record(session, user_id, problem_id)
    record.total_count += 1
    if correct:
        record.correct_count += 1
    record.last_attempt = time or datetime.datetime.now()
    session.add(record)


async def query_statistic(
    session: AsyncSession,
    *,
    problem_id: UUID | None = None,
    user_id: UUID | None = None,
) -> Any:
    raise NotImplementedError
