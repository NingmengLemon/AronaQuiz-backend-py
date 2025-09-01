import logging
import uuid
from enum import StrEnum, auto

from sqlmodel import col, delete, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..schemas.sheet import Problem, ProblemSet
from .models import DBOption, DBProblem, DBProblemSet
from .utils import dbproblem2pydproblem

logger = logging.getLogger("uvicorn.error")


class ProblemSetCreateStatus(StrEnum):
    success = auto()
    already_exists = auto()


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


async def add_problems(
    session: AsyncSession, problemset_id: uuid.UUID, *problems: Problem
) -> list[uuid.UUID] | None:
    problemset = (
        await session.exec(select(DBProblemSet).where(DBProblemSet.id == problemset_id))
    ).one_or_none()
    if problemset is None:
        return None
    added: list[uuid.UUID] = []
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
        added.append(problem_id)

    return added


async def query_problem(session: AsyncSession, problem_id: uuid.UUID) -> Problem | None:
    problem_db = (
        await session.exec(select(DBProblem).where(DBProblem.id == problem_id))
    ).one_or_none()
    return await dbproblem2pydproblem(problem_db) if problem_db is not None else None


async def search_problem(
    session: AsyncSession,
    kw: str,
    problemset_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[Problem]:
    if not kw:
        return []

    stmt = select(DBProblem)
    if problemset_id is not None:
        stmt = stmt.where(DBProblem.problemset_id == problemset_id)
    stmt = (
        stmt.outerjoin(DBOption).filter(
            or_(
                col(DBProblem.content).icontains(kw),
                col(DBOption.content).icontains(kw),
            )
        )
    ).distinct()
    page = max(1, page)
    page_size = max(0, page_size)
    if page_size != 0:
        stmt = stmt.offset(page_size * (page - 1)).limit(page_size)
    db_problems = (await session.exec(stmt)).all()
    problems = [(await dbproblem2pydproblem(p)) for p in db_problems]

    return problems


async def delete_problems(
    session: AsyncSession,
    *problem_ids: uuid.UUID,
    problemset_id: uuid.UUID | None = None,
) -> None:
    stmt = delete(DBProblem)
    if problem_ids:
        stmt = stmt.where(col(DBProblem.id).in_(problem_ids))
    if problemset_id:
        stmt = stmt.where(col(DBProblem.problemset_id) == problemset_id)
    await session.exec(stmt)  # type: ignore
    stmt = delete(DBOption)
    if problem_ids:
        stmt = stmt.where(col(DBOption.problem_id).in_(problem_ids))
    await session.exec(stmt)  # type: ignore


async def delete_problemset(
    session: AsyncSession, problemset_id: uuid.UUID
) -> None | uuid.UUID:
    problemset = (
        await session.exec(select(DBProblemSet).where(DBProblemSet.id == problemset_id))
    ).one_or_none()
    if not problemset:
        return None
    await session.delete(problemset)
    await delete_problems(session, problemset_id=problemset_id)
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
    )
    return [(await dbproblem2pydproblem(p)) for p in db_problems]


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
