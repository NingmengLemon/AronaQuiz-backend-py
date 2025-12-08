from uuid import UUID
from sqlalchemy.orm import selectinload
from sqlmodel import col, delete, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.problem import (
    DBOption,
    DBProblem,
    DBProblemSet,
)
from app.models.dto.request import ProblemSubmit
from app.models.dto.response import (
    ProblemResponse,
    ProblemSetCreateStatus,
    ProblemSetResponse,
)
from app.typ import queryable
from app.utils.db import in_transaction


async def create_problemset(
    session: AsyncSession, name: str
) -> tuple[UUID, ProblemSetCreateStatus]:
    name = name.strip()
    problemset = (
        await session.exec(select(DBProblemSet).where(DBProblemSet.name == name))
    ).one_or_none()
    if problemset is not None:
        return problemset.id, ProblemSetCreateStatus.ALREADY_EXISTS
    problemset = DBProblemSet(name=name, problems=[])
    session.add(problemset)
    await session.flush()
    await session.commit()
    return problemset.id, ProblemSetCreateStatus.SUCCESS


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
    await session.flush()
    await session.commit()
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
    await session.flush()
    await session.commit()


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
    await session.flush()
    await session.commit()
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
async def delete_all_problems(session: AsyncSession) -> None:
    # 加 type: ignore 的原因是:
    # https://github.com/fastapi/sqlmodel/issues/909
    # 按依赖顺序删除数据，先删除子表再删除父表
    await session.exec(delete(DBOption))  # type: ignore
    await session.exec(delete(DBProblem))  # type: ignore
    await session.exec(delete(DBProblemSet))  # type: ignore
