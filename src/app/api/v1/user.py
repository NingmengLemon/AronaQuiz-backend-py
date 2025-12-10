import re
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import (
    DbSessionDep,
    LoginRequired,
    RequireRoles,
    SpeedLimReqDep,
)
from app.models.db.user import UserRole
from app.models.dto.request import UserRegisterSubmit
from app.models.dto.response import (
    SelfInfoResponse,
    UserCreateResponse,
    UserInfoResponse,
)
from app.services.user import user_service

router = APIRouter(tags=["user"])


@router.get("/check_field")
async def check_userinfo_availability(
    db: DbSessionDep, field: str = Query(), value: str = Query()
) -> Literal["ok", "conflict", "invalid"]:
    """检查用户信息可用性"""
    return await user_service.check_userinfo_availability(db, field, value)


@router.post("/register")
async def register(
    db: DbSessionDep, submit: UserRegisterSubmit = Body(), _: Any = SpeedLimReqDep
) -> UserCreateResponse:
    """用户注册"""
    # 检查所有字段的可用性
    availability = await user_service.check_multiple_userinfo_availability(
        db,
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
        db,
        username=submit.username,
        email=submit.email,
        password=submit.password,
        nickname=submit.nickname,
        role=UserRole.USER,
    )
    return UserCreateResponse.model_validate(user, from_attributes=True)


@router.get("/me")
async def get_myinfo(
    login_session: LoginRequired, db: DbSessionDep
) -> SelfInfoResponse:
    """获取当前用户信息"""
    user = await user_service.query_user(db, user_id=login_session.user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    return SelfInfoResponse.model_validate(user, from_attributes=True)


@router.get("/info")
async def get_user_info(
    _: LoginRequired, db: DbSessionDep, user_id: UUID = Query()
) -> UserInfoResponse:
    """获取指定用户信息"""
    user = await user_service.query_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    return UserInfoResponse.model_validate(user, from_attributes=True)


@router.post("/delete")
async def delete_user(
    db: DbSessionDep,
    user_ids: list[UUID] = Body(),
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> list[UUID]:
    raise NotImplementedError
