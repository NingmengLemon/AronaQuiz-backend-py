import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import DbSessionDep, LoginRequired, RequireRoles
from app.models.db.user import UserRole
from app.models.dto.request import (
    ProblemSetSubmit,
    ProblemSubmit,
)
from app.models.dto.response import ApiResponse, ProblemResponse, ProblemSetCreateResponse, ProblemSetResponse
from app.models.dto.code import BusinessCode
from app.services.problem import (
    create_problemset,
    add_problems,
    delete_problems,
    get_problem_count,
    list_problemsets,
    sample_problems,
    search_problems,
)

router = APIRouter(tags=["problem"])
logger = logging.getLogger("uvicorn.error")


@router.post("/create_set", summary="创建新的题目集")
async def create_problem_set(
    session: DbSessionDep,
    problem_set: ProblemSetSubmit = Body(),
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> ApiResponse[ProblemSetCreateResponse]:
    """创建新的题目集"""
    id_, status = await create_problemset(
        session,
        problem_set.name,
    )
    
    if status == "ALREADY_EXISTS":
        return ApiResponse.error(
            code=BusinessCode.PROBLEMSET_ALREADY_EXISTS,
            message="题目集已存在",
            data=ProblemSetCreateResponse(id=id_, status=status)
        )
    
    return ApiResponse.ok(
        data=ProblemSetCreateResponse(id=id_, status=status),
        message="题目集创建成功"
    )


@router.get("/list_set", summary="列出现有的题目集")
async def list_set(session: DbSessionDep, _: LoginRequired) -> ApiResponse[list[ProblemSetResponse]]:
    """列出现有的题目集"""
    problem_sets = await list_problemsets(session)
    return ApiResponse.ok(data=problem_sets)


@router.post("/add", summary="添加题目")
async def add(
    session: DbSessionDep,
    problems: list[ProblemSubmit] = Body(),
    problemset_id: UUID = Body(),
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> ApiResponse[list[UUID]]:
    """添加题目到指定题目集"""
    result = await add_problems(
        session,
        problemset_id,
        *problems,
    )
    if result is None:
        return ApiResponse.error(
            code=BusinessCode.PROBLEMSET_NOT_FOUND,
            message=f"题目集 {problemset_id} 不存在"
        )
    return ApiResponse.ok(
        data=result,
        message=f"成功添加 {len(result)} 道题目"
    )


@router.get(
    "/search",
    summary="搜索题目",
    description="""kw 可留空, 此时不进行关键词筛选""",
)
async def search(
    session: DbSessionDep,
    _: LoginRequired,
    kw: str = Query(""),
    problemset_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
) -> ApiResponse[list[ProblemResponse]]:
    """搜索题目"""
    problems = await search_problems(
        session,
        kw.strip() or None,
        problemset_id=problemset_id,
        page=max(page, 1),
        page_size=max(page_size, 1),
    )
    return ApiResponse.ok(data=problems)


@router.get(
    "/get",
    summary="获取题目",
    description="""等价于 kw 字段留空的 /problem/search 接口""",
)
async def get_problems(
    session: DbSessionDep,
    _: LoginRequired,
    problemset_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
) -> ApiResponse[list[ProblemResponse]]:
    """获取题目列表"""
    problems = await search_problems(
        session,
        None,
        problemset_id=problemset_id,
        page=max(page, 1),
        page_size=max(page_size, 1),
    )
    return ApiResponse.ok(data=problems)


@router.get(
    "/count", summary="获取题目数量", description="习题集 ID 留空时返回库中题目总数"
)
async def get_count(
    session: DbSessionDep,
    _: LoginRequired,
    problemset_id: UUID | None = Query(None),
) -> ApiResponse[int]:
    """获取题目数量"""
    count = await get_problem_count(session, problemset_id)
    return ApiResponse.ok(data=count)


@router.post("/delete", summary="删除题目")
async def delete(
    session: DbSessionDep,
    problems: list[UUID],
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> ApiResponse[str]:
    """删除题目"""
    await delete_problems(session, *problems)
    return ApiResponse.ok(
        data="ok",
        message=f"成功删除 {len(problems)} 道题目"
    )


@router.get("/random", summary="随机抽取题目")
async def random(
    session: DbSessionDep,
    _: LoginRequired,
    problemset_id: UUID = Query(),
    n: int = Query(20),
) -> ApiResponse[list[ProblemResponse]]:
    """随机抽取题目"""
    problems = await sample_problems(session, problemset_id=problemset_id, n=n)
    return ApiResponse.ok(data=problems)