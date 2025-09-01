import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import DbSessionDep
from app.db.operations import (
    add_problems,
    delete_problems,
    get_problem_count,
    search_problem,
)
from app.schemas.sheet import Problem

router = APIRouter(tags=["problem"])
logger = logging.getLogger("uvicorn.error")


@router.post("/add")
async def add(
    session: DbSessionDep, problems: list[Problem] = Body()
) -> list[uuid.UUID]:
    return await add_problems(session, *problems)


@router.get("/search")
async def search(session: DbSessionDep, kw: str = Query()) -> list[Problem]:
    return await search_problem(session, kw)


@router.get("/count")
async def get_count(session: DbSessionDep) -> int:
    return await get_problem_count(session)


@router.post("/delete")
async def delete(session: DbSessionDep, ids: list[uuid.UUID] = Body()) -> Literal["ok"]:
    if len(ids) == 0:
        raise HTTPException(400, "需要填写将要删除的ID")
    await delete_problems(session, *ids)
    return "ok"


@router.post("/delete_all")
async def delete_all(session: DbSessionDep) -> Literal["ok"]:
    await delete_problems(session)
    return "ok"
