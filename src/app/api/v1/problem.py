import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import DbSessionDep
from app.db.decos import in_session, in_transaction
from app.db.operations import (
    add_problems,
    create_problemset,
    delete_all,
    delete_problems,
    get_problem_count,
    list_problemset,
    search_problem,
)
from app.schemas.problem import (
    CreateProblemSetResponse,
    DeleteProblemSubmit,
    ProblemResponse,
    ProblemSetResponse,
    ProblemSetSubmit,
    ProblemSubmit,
)

router = APIRouter(tags=["problem"])
logger = logging.getLogger("uvicorn.error")


@router.post("/create_set")
@in_session
@in_transaction()
async def create_problem_set(
    session: DbSessionDep, problem_set: ProblemSetSubmit = Body()
) -> CreateProblemSetResponse:
    """创建新的题目集"""
    id_, status = await create_problemset(
        session,
        problem_set.name,
    )
    return CreateProblemSetResponse(id=id_, status=status)


@router.get("/list_set")
@in_session
@in_transaction()
async def list_set(session: DbSessionDep) -> list[ProblemSetResponse]:
    """列出现有的题目集"""
    return await list_problemset(session)


@router.post("/add")
@in_session
@in_transaction()
async def add(
    session: DbSessionDep,
    problems: list[ProblemSubmit] = Body(),
    problemset_id: uuid.UUID = Body(),
) -> list[uuid.UUID]:
    """添加题目"""
    result = await add_problems(
        session,
        problemset_id,
        *problems,
    )
    if result is None:
        raise HTTPException(404, f"题目集 {problemset_id} 不存在")
    return result


@router.get("/search")
@in_session
@in_transaction()
async def search(
    session: DbSessionDep,
    kw: str = Query(),
    problemset_id: uuid.UUID | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
    user_id: uuid.UUID | None = Query(None),
) -> list[ProblemResponse]:
    """搜索题目

    每道题目额外带有给定用户id的正确率统计数据, 留空默认为 anonymous 共享用户"""
    kw = kw.strip()
    if not kw:
        raise HTTPException(400, "缺失搜索关键字")
    return await search_problem(
        session,
        kw,
        problemset_id=problemset_id,
        page=page,
        page_size=page_size,
        user_id=user_id,
    )


@router.get("/get")
@in_session
@in_transaction()
async def get_problems(
    session: DbSessionDep,
    problemset_id: uuid.UUID | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
    user_id: uuid.UUID | None = Query(None),
) -> list[ProblemResponse]:
    """获取题目

    每道题目额外带有给定用户id的正确率统计数据, 留空默认为 anonymous 共享用户"""
    return await search_problem(
        session,
        None,
        problemset_id=problemset_id,
        page=page,
        page_size=page_size,
        user_id=user_id,
    )


@router.get("/count")
@in_session
@in_transaction()
async def get_count(
    session: DbSessionDep,
    problemset_id: uuid.UUID | None = Query(None),
) -> int:
    """获取题目数量

    习题集id留空则返回库中题目总数"""
    return await get_problem_count(session, problemset_id)


@router.post("/delete")
@in_session
@in_transaction()
async def delete(
    session: DbSessionDep, problems: DeleteProblemSubmit = Body()
) -> Literal["ok"]:
    """删除题目"""
    if len(problems.ids) == 0:
        raise HTTPException(400, "需要填写将要删除的ID")
    await delete_problems(session, *problems.ids)
    return "ok"


@router.post("/_delete_all")
@in_session
@in_transaction()
async def delete_all_problemsets(session: DbSessionDep) -> Literal["ok"]:
    """删除全部题目

    **仅供调试**"""
    await delete_all(session)
    return "ok"
