import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import DbSessionDep, LoginRequired, ProblemServiceDep, RequireRoles
from app.models.db.user import UserRole
from app.models.dto.code import BusinessCode
from app.models.dto.request import (
    ProblemSetSubmit,
    ProblemSubmit,
)
from app.models.dto.response import (
    ApiResponse,
    ProblemResponse,
    ProblemSetCreateResponse,
    ProblemSetResponse,
)

router = APIRouter(tags=["problems"])
logger = logging.getLogger("uvicorn.error")


@router.post(
    "/problemsets",
    summary="创建新的题目集",
    status_code=201,
)
async def create_problem_set(
    problem_service: ProblemServiceDep,
    problem_set: ProblemSetSubmit = Body(),
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> ApiResponse[ProblemSetCreateResponse]:
    """创建新的题目集"""
    id_, status = await problem_service.create_problemset(
        problem_set.name,
    )

    if status == "ALREADY_EXISTS":
        raise HTTPException(
            status_code=409,
            detail=ApiResponse.error(
                code=BusinessCode.PROBLEMSET_ALREADY_EXISTS,
                message="题目集已存在",
                data=ProblemSetCreateResponse(id=id_, status=status),
            ).model_dump(),
        )

    return ApiResponse.ok(
        data=ProblemSetCreateResponse(id=id_, status=status), message="题目集创建成功"
    )


@router.get(
    "/problemsets",
    summary="列出现有的题目集",
)
async def list_problem_sets(
    problem_service: ProblemServiceDep, _: LoginRequired
) -> ApiResponse[list[ProblemSetResponse]]:
    """列出现有的题目集"""
    problem_sets = await problem_service.list_problemsets()
    return ApiResponse.ok(data=problem_sets)


@router.post(
    "/problems",
    summary="添加题目",
    status_code=201,
)
async def create_problems(
    problem_service: ProblemServiceDep,
    problems: list[ProblemSubmit] = Body(),
    problemset_id: UUID = Body(),
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> ApiResponse[list[UUID]]:
    """添加题目到指定题目集"""
    result = await problem_service.add_problems(
        problemset_id,
        *problems,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=ApiResponse.error(
                code=BusinessCode.PROBLEMSET_NOT_FOUND,
                message=f"题目集 {problemset_id} 不存在",
            ).model_dump(),
        )
    return ApiResponse.ok(data=result, message=f"成功添加 {len(result)} 道题目")


@router.get(
    "/problems",
    summary="搜索题目",
    description="""支持关键词搜索、题目集筛选和分页""",
)
async def search_problems(
    problem_service: ProblemServiceDep,
    _: LoginRequired,
    keyword: str = Query("", description="搜索关键词，留空则不进行关键词筛选"),
    problemset_id: UUID | None = Query(
        None, description="题目集ID，留空则搜索所有题目集"
    ),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=10000, description="每页数量"),
) -> ApiResponse[list[ProblemResponse]]:
    """搜索题目"""
    problems = await problem_service.search_problems(
        keyword.strip() or None,
        problemset_id=problemset_id,
        page=max(page, 1),
        page_size=max(page_size, 1),
    )
    return ApiResponse.ok(data=problems)


@router.get(
    "/problems/count",
    summary="获取题目数量",
    description="题目集ID留空时返回库中题目总数",
)
async def get_problem_count(
    problem_service: ProblemServiceDep,
    _: LoginRequired,
    problemset_id: UUID | None = Query(None, description="题目集ID"),
) -> ApiResponse[int]:
    """获取题目数量"""
    count = await problem_service.get_problem_count(problemset_id)
    return ApiResponse.ok(data=count)


@router.get(
    "/problems/random",
    summary="随机抽取题目",
)
async def get_random_problems(
    problem_service: ProblemServiceDep,
    _: LoginRequired,
    problemset_id: UUID = Query(description="题目集ID"),
    n: int = Query(20, ge=1, le=1000, description="抽取数量"),
) -> ApiResponse[list[ProblemResponse]]:
    """随机抽取题目"""
    problems = await problem_service.sample_problems(problemset_id=problemset_id, n=n)
    return ApiResponse.ok(data=problems)


@router.delete(
    "/problems",
    summary="删除题目",
    status_code=204,
)
async def delete_problems(
    problem_service: ProblemServiceDep,
    problem_ids: list[UUID] = Body(),
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> None:
    """删除题目"""
    await problem_service.delete_problems(*problem_ids)
