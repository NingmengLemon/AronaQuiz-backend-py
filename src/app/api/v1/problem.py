import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import DbSessionDep
from app.db.operations import (
    add_problems,
    create_problemset,
    delete_problems,
    get_problem_count,
    list_problemset,
    sample,
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
async def create_problem_set(
    session: DbSessionDep, problem_set: ProblemSetSubmit = Body()
) -> CreateProblemSetResponse:
    id_, status = await create_problemset(
        session,
        problem_set.name,
    )
    return CreateProblemSetResponse(id=id_, status=status)


@router.get("/list_set", summary="列出现有的题目集")
async def list_set(session: DbSessionDep) -> list[ProblemSetResponse]:
    return await list_problemset(session)


@router.post("/add", summary="添加题目")
async def add(
    session: DbSessionDep,
    problems: list[ProblemSubmit] = Body(),
    problemset_id: UUID = Body(),
) -> list[UUID]:
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
    description="""kw 可留空, 此时不进行关键词筛选""",
)
async def search(
    session: DbSessionDep,
    kw: str = Query(""),
    problemset_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
) -> list[ProblemResponse]:
    return await search_problem(
        session,
        kw.strip() or None,
        problemset_id=problemset_id,
        page=max(page, 1),
        page_size=max(page_size, 1),
    )


@router.get(
    "/get",
    summary="获取题目",
    description="""等价于 kw 字段留空的 /problem/search 接口""",
)
async def get_problems(
    session: DbSessionDep,
    problemset_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
) -> list[ProblemResponse]:
    return await search_problem(
        session,
        None,
        problemset_id=problemset_id,
        page=max(page, 1),
        page_size=max(page_size, 1),
    )


@router.get(
    "/count", summary="获取题目数量", description="习题集 ID 留空时返回库中题目总数"
)
async def get_count(
    session: DbSessionDep,
    problemset_id: UUID | None = Query(None),
) -> int:
    return await get_problem_count(session, problemset_id)


@router.post("/delete", summary="删除题目")
async def delete(session: DbSessionDep, problems: list[UUID]) -> Literal["ok"]:
    await delete_problems(session, *problems)
    return "ok"


@router.get("/random", summary="随机抽取题目")
async def random(
    session: DbSessionDep, problemset_id: UUID = Query(), n: int = Query(20)
) -> list[ProblemSubmit]:
    return await sample(session, problemset_id=problemset_id, n=n)
