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
    search_problem,
)
from app.schemas.sheet import Problem

router = APIRouter(tags=["problem"])
logger = logging.getLogger("uvicorn.error")


class CreateSetResp(BaseModel):
    id: uuid.UUID
    status: ProblemSetCreateStatus


@router.post("/create_set")
async def create_set(session: DbSessionDep, name: str) -> CreateSetResp:
    id_, status = await create_problemset(session, name)
    return CreateSetResp(id=id_, status=status)


@router.post("/add")
async def add(
    session: DbSessionDep,
    problems: list[Problem] = Body(),
    problemset_id: uuid.UUID = Body(),
) -> list[uuid.UUID]:
    result = await add_problems(session, problemset_id, *problems)
    if result is None:
        raise HTTPException(404, f"problem set {problemset_id} not found")
    return result


@router.get("/search")
async def search(
    session: DbSessionDep,
    kw: str = Query(),
    problemset_id: uuid.UUID | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
) -> list[Problem]:
    return await search_problem(session, kw, problemset_id, page, page_size)


@router.get("/count")
async def get_count(
    session: DbSessionDep,
    problemset_id: uuid.UUID | None = Query(None),
) -> int:
    return await get_problem_count(session, problemset_id)


@router.post("/delete")
async def delete(session: DbSessionDep, ids: list[uuid.UUID] = Body()) -> Literal["ok"]:
    if len(ids) == 0:
        raise HTTPException(400, "需要填写将要删除的ID")
    await delete_problems(session, *ids)
    return "ok"


@router.post("/delete_all")
async def delete_all(
    session: DbSessionDep, problemset_id: uuid.UUID | None = Body(None)
) -> Literal["ok"]:
    await delete_problems(session, problemset_id=problemset_id)
    return "ok"
