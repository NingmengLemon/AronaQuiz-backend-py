"""标签相关API端点"""

import logging
from uuid import UUID

from fastapi import APIRouter, Body, Query

from app.api.deps import LoginRequired, RequireRoles, TagServiceDep
from app.exceptions import APIException
from app.models.db.user import UserRole
from app.models.dto.code import BusinessCode
from app.models.dto.request import TagCreateRequest, TagUpdateRequest
from app.models.dto.response import (
    ApiResponse,
    TagCreateResponse,
    TagDetailResponse,
    TagListResponse,
    TagProblemResponse,
    TagProblemsResponse,
    TagProblemSetResponse,
    TagProblemSetsResponse,
    TagResponse,
    TagUpdateResponse,
)
from app.services.problem import TAG_NAME_CONSTRAINT_REGEX
from app.utils.response import ResponseUtil

router = APIRouter(tags=["tags"])
logger = logging.getLogger("uvicorn.error")


@router.get(
    "/tags",
    summary="获取标签列表",
    description="支持关键词搜索和分页",
)
async def list_tags(
    tag_service: TagServiceDep,
    current_user: LoginRequired,
    keyword: str = Query("", description="搜索关键词，留空则返回所有标签"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
) -> ApiResponse[TagListResponse]:
    """获取标签列表"""
    tags = await tag_service.list_tags(
        keyword=keyword.strip() or None,
        page=page,
        page_size=page_size,
    )

    total = await tag_service.count_tags(keyword=keyword.strip() or None)

    tag_responses = [TagResponse(id=tag.id, name=tag.name) for tag in tags]

    return ResponseUtil.success(
        data=TagListResponse(
            tags=tag_responses,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get(
    "/tags/{tag_id}",
    summary="获取标签详情",
)
async def get_tag(
    tag_service: TagServiceDep,
    current_user: LoginRequired,
    tag_id: UUID,
) -> ApiResponse[TagDetailResponse]:
    """根据ID获取标签详情"""
    tag = await tag_service.get_tag_by_id(tag_id)
    if not tag:
        raise APIException(
            status_code=404,
            code=BusinessCode.NOT_FOUND,
            message=f"标签 {tag_id} 不存在",
        )

    # 获取关联的题目和题目集数量
    problems = await tag_service.get_tag_problems(tag_id)
    problemsets = await tag_service.get_tag_problemsets(tag_id)

    return ResponseUtil.success(
        data=TagDetailResponse(
            id=tag.id,
            name=tag.name,
            problem_count=len(problems),
            problemset_count=len(problemsets),
        )
    )


@router.post(
    "/tags",
    summary="创建新标签",
    status_code=201,
)
async def create_tag(
    tag_service: TagServiceDep,
    tag_data: TagCreateRequest = Body(),
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> ApiResponse[TagCreateResponse]:
    """创建新标签（需要管理员权限）"""
    # 验证标签名称格式（使用与ProblemService相同的正则表达式）

    if not TAG_NAME_CONSTRAINT_REGEX.match(tag_data.name):
        raise APIException(
            status_code=400,
            code=BusinessCode.VALIDATION_ERROR,
            message="标签名称只能包含字母、数字、下划线和连字符，且长度在1-30个字符之间",
        )

    tag = await tag_service.create_tag(tag_data.name)

    return ResponseUtil.created(
        data=TagCreateResponse(
            id=tag.id,
            name=tag.name,
            message="标签创建成功",
        ),
        message="标签创建成功",
    )


@router.put(
    "/tags/{tag_id}",
    summary="更新标签",
)
async def update_tag(
    tag_service: TagServiceDep,
    tag_id: UUID,
    tag_data: TagUpdateRequest = Body(),
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> ApiResponse[TagUpdateResponse]:
    """更新标签名称（需要管理员权限）"""
    # 验证标签名称格式
    import re

    TAG_NAME_CONSTRAINT_REGEX = re.compile(r"^[\w\-]{1,30}$")

    if not TAG_NAME_CONSTRAINT_REGEX.match(tag_data.name):
        raise APIException(
            status_code=400,
            code=BusinessCode.VALIDATION_ERROR,
            message="标签名称只能包含字母、数字、下划线和连字符，且长度在1-30个字符之间",
        )

    # 获取原始标签信息并保存原始名称
    original_tag = await tag_service.get_tag_by_id(tag_id)
    if not original_tag:
        raise APIException(
            status_code=404,
            code=BusinessCode.NOT_FOUND,
            message=f"标签 {tag_id} 不存在",
        )
    original_name = original_tag.name  # 保存原始名称

    updated_tag = await tag_service.update_tag(tag_id, tag_data.name)
    if not updated_tag:
        raise APIException(
            status_code=404,
            code=BusinessCode.NOT_FOUND,
            message=f"标签 {tag_id} 不存在",
        )

    return ResponseUtil.success(
        data=TagUpdateResponse(
            id=updated_tag.id,
            old_name=original_name,  # 使用保存的原始名称
            new_name=updated_tag.name,
            message="标签更新成功",
        ),
        message="标签更新成功",
    )


@router.delete(
    "/tags/{tag_id}",
    summary="删除标签",
    status_code=204,
)
async def delete_tag(
    tag_service: TagServiceDep,
    tag_id: UUID,
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> None:
    """删除标签（需要管理员权限）"""
    success = await tag_service.delete_tag(tag_id)
    if not success:
        raise APIException(
            status_code=404,
            code=BusinessCode.NOT_FOUND,
            message=f"标签 {tag_id} 不存在",
        )


@router.get(
    "/tags/{tag_id}/problems",
    summary="获取使用该标签的题目",
)
async def get_tag_problems(
    tag_service: TagServiceDep,
    current_user: LoginRequired,
    tag_id: UUID,
) -> ApiResponse[TagProblemsResponse]:
    """获取使用该标签的所有题目"""
    tag = await tag_service.get_tag_by_id(tag_id)
    if not tag:
        raise APIException(
            status_code=404,
            code=BusinessCode.NOT_FOUND,
            message=f"标签 {tag_id} 不存在",
        )

    problems = await tag_service.get_tag_problems(tag_id)

    # 转换为结构化的响应格式
    problem_responses = [
        TagProblemResponse(
            id=problem.id,
            content=problem.content,
            type=problem.type,
            problemset_id=problem.problemset_id,
        )
        for problem in problems
    ]

    return ResponseUtil.success(
        data=TagProblemsResponse(
            tag=TagResponse(id=tag.id, name=tag.name),
            problems=problem_responses,
            total=len(problem_responses),
        )
    )


@router.get(
    "/tags/{tag_id}/problemsets",
    summary="获取使用该标签的题目集",
)
async def get_tag_problemsets(
    tag_service: TagServiceDep,
    current_user: LoginRequired,
    tag_id: UUID,
) -> ApiResponse[TagProblemSetsResponse]:
    """获取使用该标签的所有题目集"""
    tag = await tag_service.get_tag_by_id(tag_id)
    if not tag:
        raise APIException(
            status_code=404,
            code=BusinessCode.NOT_FOUND,
            message=f"标签 {tag_id} 不存在",
        )

    problemsets = await tag_service.get_tag_problemsets(tag_id)

    # 转换为结构化的响应格式
    problemset_responses = [
        TagProblemSetResponse(
            id=problemset.id,
            name=problemset.name,
            description=problemset.description,
            is_public=problemset.is_public,
            owner_id=problemset.owner_id,
        )
        for problemset in problemsets
    ]

    return ResponseUtil.success(
        data=TagProblemSetsResponse(
            tag=TagResponse(id=tag.id, name=tag.name),
            problemsets=problemset_responses,
            total=len(problemset_responses),
        )
    )
