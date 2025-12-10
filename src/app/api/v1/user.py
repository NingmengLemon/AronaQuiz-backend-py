import re
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import validate_email
from pydantic_core import PydanticCustomError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import (
    DbSessionDep,
    LoginRequired,
    RequireRoles,
    SpeedLimReqDep,
)
from app.models.db.user import DBUser, UserRole
from app.models.dto.request import UserRegisterSubmit
from app.models.dto.response import (
    SelfInfoResponse,
    UserCreateResponse,
    UserInfoResponse,
)
from app.repos.user import UserRepository
from app.services.user import user_service

router = APIRouter(tags=["user"])
USERNAME_REGEX = re.compile(r"^[A-Za-z0-9_\-]{3,16}$", re.U | re.I)
NICKNAME_REGEX = re.compile(
    r"^[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AFa-zA-Z0-9\u00C0-\u00FF_-]{2,16}$",
    re.U | re.I,
)

USER_FIELD_MAP: dict[str, Any] = {
    "email": DBUser.email,
    "username": DBUser.username,
    "nickname": DBUser.nickname,
}


async def _check_userinfo_availability(
    db: AsyncSession, field: str, value: str
) -> Literal["ok", "conflict", "invalid"]:
    if field not in USER_FIELD_MAP:
        return "invalid"
    match field:
        case "email":
            try:
                validate_email(value)
            except PydanticCustomError:
                return "invalid"
        case "username":
            if USERNAME_REGEX.match(value) is None:
                return "invalid"
        case "nickname":
            if NICKNAME_REGEX.match(value) is None:
                return "invalid"

    # 检查数据库中是否已存在
    user_repo = UserRepository()
    if field == "email":
        user = await user_repo.get_by_email(db, value)
    elif field == "username":
        user = await user_repo.get_by_username(db, value)
    elif field == "nickname":
        user = await user_repo.get_by_field(db, "nickname", value)
    else:
        user = None

    if user is not None:
        return "conflict"
    return "ok"


@router.get("/check_field")
async def check_userinfo_availability(
    db: DbSessionDep, field: str = Query(), value: str = Query()
) -> Literal["ok", "conflict", "invalid"]:
    return await _check_userinfo_availability(db, field, value)


@router.post("/register")
async def register(
    db: DbSessionDep, submit: UserRegisterSubmit = Body(), _: Any = SpeedLimReqDep
) -> UserCreateResponse:
    """用户注册"""
    for field, value in zip(
        USER_FIELD_MAP.keys(), (submit.email, submit.username, submit.nickname)
    ):
        if (
            field_status := await _check_userinfo_availability(db, field, value)
        ) != "ok":
            raise HTTPException(
                400, f"用户信息不可用: {field}: `{value}` ({field_status})"
            )

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
