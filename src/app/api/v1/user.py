from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import (
    DbSessionDep,
    LoginRequired,
    RequireRoles,
    SpeedLimReqDep,
    UserServiceDep,
)
from app.models.db.user import UserRole
from app.models.dto.request import UserRegisterSubmit
from app.models.dto.response import (
    SelfInfoResponse,
    UserCreateResponse,
    UserInfoResponse,
)

router = APIRouter(tags=["users"])


@router.get(
    "/users/check-availability",
    summary="检查用户信息可用性",
    description="检查用户名、邮箱或昵称是否可用",
)
async def check_userinfo_availability(
    user_service: UserServiceDep,
    field: str = Query(description="字段名"),
    value: str = Query(description="要检查的值"),
) -> Literal["ok", "conflict", "invalid"]:
    """检查用户信息可用性"""
    return await user_service.check_userinfo_availability(field, value)


@router.post(
    "/users",
    summary="用户注册",
    status_code=201,
)
async def create_user(
    user_service: UserServiceDep,
    submit: UserRegisterSubmit = Body(),
    _: Any = SpeedLimReqDep,
) -> UserCreateResponse:
    """用户注册"""
    # 检查所有字段的可用性
    availability = await user_service.check_multiple_userinfo_availability(
        username=submit.username,
        email=submit.email,
        nickname=submit.nickname,
    )

    # 检查是否有冲突或无效
    for field, status in availability.items():
        if status != "ok":
            value = getattr(submit, field)
            raise HTTPException(400, f"用户信息不可用: {field}: `{value}` ({status})")

    user = await user_service.create_user(
        username=submit.username,
        email=submit.email,
        password=submit.password,
        nickname=submit.nickname,
        role=UserRole.USER,
    )
    return UserCreateResponse.model_validate(user, from_attributes=True)


@router.get(
    "/users/me",
    summary="获取当前用户信息",
)
async def get_current_user(
    login_session: LoginRequired,
    user_service: UserServiceDep,
) -> SelfInfoResponse:
    """获取当前用户信息"""
    user = await user_service.query_user(user_id=login_session.user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    return SelfInfoResponse.model_validate(user, from_attributes=True)


@router.get(
    "/users/{user_id}",
    summary="获取指定用户信息",
)
async def get_user_by_id(
    _: LoginRequired,
    user_service: UserServiceDep,
    user_id: UUID,
) -> UserInfoResponse:
    """获取指定用户信息"""
    user = await user_service.query_user(user_id=user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    return UserInfoResponse.model_validate(user, from_attributes=True)


@router.delete(
    "/users/{user_id}",
    summary="删除用户",
    status_code=204,
)
async def delete_user(
    db: DbSessionDep,
    user_id: UUID,
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> None:
    """删除用户"""
    raise NotImplementedError
