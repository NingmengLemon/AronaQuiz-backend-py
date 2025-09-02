import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import DbSessionDep
from app.db.operations import (
    ProblemSetCreateStatus,
    add_problems,
    create_problemset,
    delete_problems,
    get_problem_count,
    list_problemset,
    search_problem,
)
from app.decos import in_session, in_transaction
from app.schemas.problem import BaseProblem as ProblemSubmit
from app.schemas.problem import Problem, ProblemSet, ProblemWithStat

router = APIRouter(tags=["problem"])
logger = logging.getLogger("uvicorn.error")


class CreateSetResp(BaseModel):
    id: uuid.UUID
    status: ProblemSetCreateStatus


@router.post("/create_set")
@in_session
@in_transaction
async def create_set(session: DbSessionDep, name: str) -> CreateSetResp:
    id_, status = await create_problemset(session, name)
    return CreateSetResp(id=id_, status=status)


@router.get("/list_set")
@in_session
@in_transaction
async def list_set(session: DbSessionDep) -> list[ProblemSet]:
    return await list_problemset(session)


@router.post("/add")
@in_session
@in_transaction
async def add(
    session: DbSessionDep,
    problems: list[ProblemSubmit] = Body(),
    problemset_id: uuid.UUID = Body(),
) -> list[uuid.UUID]:
    result = await add_problems(
        session,
        problemset_id,
        *[Problem.model_validate(p) for p in problems],
    )
    if result is None:
        raise HTTPException(404, f"problem set {problemset_id} not found")
    return result


@router.get("/search")
@in_session
@in_transaction
async def search(
    session: DbSessionDep,
    kw: str = Query(),
    problemset_id: uuid.UUID | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
) -> list[ProblemWithStat]:
    return await search_problem(session, kw, problemset_id, page, page_size)


@router.get("/get")
@in_session
@in_transaction
async def get_problems(
    session: DbSessionDep,
    problemset_id: uuid.UUID | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
) -> list[ProblemWithStat]:
    return await search_problem(session, None, problemset_id, page, page_size)


@router.get("/count")
@in_session
@in_transaction
async def get_count(
    session: DbSessionDep,
    problemset_id: uuid.UUID | None = Query(None),
) -> int:
    return await get_problem_count(session, problemset_id)


@router.post("/delete")
@in_session
@in_transaction
async def delete(session: DbSessionDep, ids: list[uuid.UUID] = Body()) -> Literal["ok"]:
    if len(ids) == 0:
        raise HTTPException(400, "需要填写将要删除的ID")
    await delete_problems(session, *ids)
    return "ok"


@router.post("/delete_all")
@in_session
@in_transaction
async def delete_all(
    session: DbSessionDep, problemset_id: uuid.UUID = Body(None)
) -> Literal["ok"]:
    await delete_all(session, problemset_id=problemset_id)
    return "ok"
