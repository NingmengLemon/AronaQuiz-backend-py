import datetime
import logging
import uuid
from enum import Enum, StrEnum, auto
from typing import Any, ParamSpec, TypeVar, cast, overload

from sqlalchemy.orm import QueryableAttribute, selectinload
from sqlmodel import and_, col, delete, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.decos import in_transaction

from ..schemas.problem import Problem, ProblemSet, ProblemWithStat
from .models import DBAnswerRecord, DBOption, DBProblem, DBProblemSet, DBUser

logger = logging.getLogger("uvicorn.error")
T = TypeVar("T")
P = ParamSpec("P")

DEFAULT_USERNAME = "anonymous"


class VoidType(Enum):
    VOID = type("_VOID", (), {})


class ProblemSetCreateStatus(StrEnum):
    success = auto()
    already_exists = auto()


def queryable(o: T) -> QueryableAttribute[T]:
    return cast(QueryableAttribute, o)


@in_transaction()
async def create_problemset(
    session: AsyncSession, name: str
) -> tuple[uuid.UUID, ProblemSetCreateStatus]:
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
    session: AsyncSession, problemset_id: uuid.UUID, *problems: Problem
) -> list[uuid.UUID] | None:
    problemset = (
        await session.exec(select(DBProblemSet).where(DBProblemSet.id == problemset_id))
    ).one_or_none()
    if problemset is None:
        return None
    added_ids: list[uuid.UUID] = []
    for problem in problems:
        problem_db = DBProblem.model_validate(
            problem,
            update={
                "options": [],
                "problemset_id": problemset.id,
                "problemset": problemset,
                "id": uuid.uuid4(),
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


async def query_problem(session: AsyncSession, problem_id: uuid.UUID) -> Problem | None:
    """not public"""
    problem_db = (
        await session.exec(
            select(DBProblem)
            .where(DBProblem.id == problem_id)
            .options(selectinload(queryable(DBProblem.options)))
        )
    ).one_or_none()
    return (
        Problem.model_validate(problem_db, from_attributes=True)
        if problem_db is not None
        else None
    )


async def search_problem(
    session: AsyncSession,
    kw: str | None = None,
    problemset_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    user_id: uuid.UUID | None | VoidType = VoidType.VOID,
) -> list[ProblemWithStat]:
    stmt = select(
        DBProblem,
        func.coalesce(DBAnswerRecord.correct_count, 0).label("correct_count"),
        func.coalesce(DBAnswerRecord.total_count, 0).label("total_count"),
    )
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
    stmt = stmt.outerjoin(
        DBAnswerRecord,
        and_(
            (DBAnswerRecord.problem_id == DBProblem.id),
            (
                DBAnswerRecord.user_id
                == (
                    user_id
                    if user_id is uuid.UUID
                    else (await ensure_user(session, DEFAULT_USERNAME)).id
                )
            ),
        ),
    )
    page = max(1, page)
    page_size = max(0, page_size)
    if page_size != 0:
        stmt = stmt.offset(page_size * (page - 1)).limit(page_size)
    db_problems = (
        await session.exec(stmt.options(selectinload(queryable(DBProblem.options))))
    ).all()
    result: list[ProblemWithStat] = []
    for p, c, t in db_problems:
        result.append(ProblemWithStat.model_validate(p, from_attributes=True))
        result[-1].correct_count = c
        result[-1].total_count = t

    return result


@in_transaction()
async def delete_problems(
    session: AsyncSession,
    *problem_ids: uuid.UUID,
) -> None:
    stmt = delete(DBProblem)
    stmt = stmt.where(col(DBProblem.id).in_(problem_ids))
    await session.exec(stmt)  # type: ignore
    stmt = delete(DBOption)
    stmt = stmt.where(col(DBOption.problem_id).in_(problem_ids))
    await session.exec(stmt)  # type: ignore


@in_transaction()
async def delete_problemset(
    session: AsyncSession, problemset_id: uuid.UUID
) -> None | uuid.UUID:
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
    session: AsyncSession, problemset_id: uuid.UUID | None = None
) -> int:
    stmt = select(func.count())
    if problemset_id:
        stmt = stmt.where(DBProblem.problemset_id == problemset_id)
    return (await session.exec(stmt.select_from(DBProblem))).one()


async def sample(
    session: AsyncSession, problemset_id: uuid.UUID, n: int = 20
) -> list[Problem]:
    db_problems = await session.exec(
        select(DBProblem)
        .where(DBProblem.problemset_id == problemset_id)
        .order_by(func.random())
        .limit(n)
        .options(selectinload(queryable(DBProblem.options)))
    )
    return [Problem.model_validate(p, from_attributes=True) for p in db_problems]


async def list_problemset(session: AsyncSession) -> list[ProblemSet]:
    dbproblemsets = (await session.exec(select(DBProblemSet))).all()
    return [
        ProblemSet(id=ps.id, name=ps.name, count=cnt)
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
async def query_user(session: AsyncSession, *, user_id: uuid.UUID) -> DBUser | None: ...


async def query_user(
    session: AsyncSession,
    *,
    username: str | None = None,
    user_id: uuid.UUID | None = None,
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
    user = DBUser(username=username)
    session.add(user)
    return user


async def ensure_user(session: AsyncSession, username: str) -> DBUser:
    if (user := await query_user(session, username=username)) is None:
        user = await create_user(session, username)
    return user


@in_transaction()
async def create_record(
    session: AsyncSession, user_id: uuid.UUID, problem_id: uuid.UUID
) -> DBAnswerRecord:
    record = DBAnswerRecord(user_id=user_id, problem_id=problem_id)
    session.add(record)
    return record


async def ensure_record(
    session: AsyncSession, user_id: uuid.UUID, problem_id: uuid.UUID
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
    problem_id: uuid.UUID,
    user_id: uuid.UUID,
    correct: bool,
    time: datetime.datetime | None = None,
) -> None:
    problem = await query_problem(session, problem_id)
    if problem is None:
        raise ValueError("no problem found")
    record = await ensure_record(session, user_id, problem_id)
    record.total_count += 1
    if correct:
        record.correct_count += 1
    record.last_attempt = time or datetime.datetime.now()
    session.add(record)


async def query_statistic(
    session: AsyncSession,
    *,
    problem_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> Any:
    return NotImplemented
