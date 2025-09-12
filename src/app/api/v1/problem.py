import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import DbSessionDep
from app.db.decos import in_session, in_transaction
from app.db.operations import (
    add_problems,
    create_problemset,
    delete_problems,
    get_problem_count,
    list_problemset,
    search_problem,
)
from app.schemas.request import (
    ProblemSetSubmit,
    ProblemSubmit,
)
from app.schemas.response import (
    CreateProblemSetResponse,
    ProblemResponse,
    ProblemSetResponse,
)

router = APIRouter(tags=["problem"])
logger = logging.getLogger("uvicorn.error")


@router.post("/create_set", summary="创建新的题目集")
@in_session
@in_transaction()
async def create_problem_set(
    session: DbSessionDep, problem_set: ProblemSetSubmit = Body()
) -> CreateProblemSetResponse:
    id_, status = await create_problemset(
        session,
        problem_set.name,
    )
    return CreateProblemSetResponse(id=id_, status=status)


@router.get("/list_set", summary="列出现有的题目集")
@in_session
@in_transaction()
async def list_set(session: DbSessionDep) -> list[ProblemSetResponse]:
    return await list_problemset(session)


@router.post("/add", summary="添加题目")
@in_session
@in_transaction()
async def add(
    session: DbSessionDep,
    problems: list[ProblemSubmit] = Body(),
    problemset_id: uuid.UUID = Body(),
) -> list[uuid.UUID]:
    result = await add_problems(
        session,
        problemset_id,
        *problems,
    )
    if result is None:
        raise HTTPException(404, f"题目集 {problemset_id} 不存在")
    return result


@router.get(
    "/search",
    summary="搜索题目",
    description="""kw 可传入空字符串或留空, 此时不进行关键词筛选

page_size 可填 0 表示不进行分页, 此时 page 被视为 1""",
)
@in_session
@in_transaction()
async def search(
    session: DbSessionDep,
    kw: str = Query(""),
    problemset_id: uuid.UUID | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
) -> list[ProblemResponse]:
    return await search_problem(
        session,
        kw.strip() or None,
        problemset_id=problemset_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/get",
    summary="获取题目",
    description="""等价于 kw 字段留空的 /problem/search 接口

page_size 可填 0 表示不进行分页, 此时 page 被视为 1""",
)
@in_session
@in_transaction()
async def get_problems(
    session: DbSessionDep,
    problemset_id: uuid.UUID | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
) -> list[ProblemResponse]:
    return await search_problem(
        session,
        None,
        problemset_id=problemset_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/count", summary="获取题目数量", description="习题集 ID 留空时返回库中题目总数"
)
@in_session
@in_transaction()
async def get_count(
    session: DbSessionDep,
    problemset_id: uuid.UUID | None = Query(None),
) -> int:
    return await get_problem_count(session, problemset_id)


@router.post("/delete", summary="删除题目")
@in_session
@in_transaction()
async def delete(session: DbSessionDep, problems: list[uuid.UUID]) -> Literal["ok"]:
    await delete_problems(session, *problems)
    return "ok"
