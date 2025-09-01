import uuid

from sqlalchemy import delete
from sqlmodel import col, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..schemas.sheet import Problem
from .models import Option as DBOption
from .models import Problem as DBProblem


async def add_problems(session: AsyncSession, *problems: Problem) -> list[uuid.UUID]:
    added: list[uuid.UUID] = []
    for problem in problems:
        problem_db = DBProblem.model_validate(
            problem,
            update={
                "options": [],
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
    return Problem.model_validate(problem_db)


async def search_problem(
    session: AsyncSession,
    kw: str,
    page: int = 1,
    page_size: int = 20,
) -> list[Problem]:
    if not kw:
        return []

    stmt = select(DBProblem).filter(
        or_(
            col(DBProblem.content).icontains(kw),
            col(DBOption.content).icontains(kw),
        )
    )
    page = max(1, page)
    page_size = max(0, page)
    if page_size != 0:
        stmt = stmt.offset(page_size * page - 1).limit(page_size)
    problems = [Problem.model_validate(p) for p in (await session.exec(stmt)).all()]

    return problems


async def delete_problems(session: AsyncSession, *problem_ids: uuid.UUID) -> None:
    await session.delete(select(DBProblem).where(col(DBProblem.id).in_(problem_ids)))


async def delete_all_problems(session: AsyncSession) -> None:
    await session.exec(delete(DBProblem))  # type: ignore


async def get_problem_count(session: AsyncSession) -> int:
    return (await session.exec(select(func.count()).select_from(DBProblem))).one()
