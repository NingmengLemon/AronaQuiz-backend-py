import re
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import validate_email
from pydantic_core import PydanticCustomError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import DbSessionDep, LoginRequired, SpeedLimReqDep
from app.db.models import DBUser, UserRole
from app.db.operations import create_user
from app.schemas.request import UserRegisterSubmit
from app.schemas.response import SelfInfoResponse, UserCreateResponse, UserInfoResponse

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
    if (
        await db.exec(select(DBUser).where(USER_FIELD_MAP[field] == value))
    ).one_or_none():
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
    for field, value in zip(
        USER_FIELD_MAP.keys(), (submit.email, submit.username, submit.nickname)
    ):
        if (
            field_status := await _check_userinfo_availability(db, field, value)
        ) != "ok":
            raise HTTPException(
                400, f"用户信息不可用: {field}: `{value}` ({field_status})"
            )

    user_id = await create_user(db, **submit.model_dump(), role=UserRole.USER)
    return UserCreateResponse(user_id=user_id)


@router.get("/me")
async def get_myinfo(user_id: LoginRequired, db: DbSessionDep) -> SelfInfoResponse:
    user = (await db.exec(select(DBUser).where(DBUser.id == user_id))).one()
    return SelfInfoResponse.model_validate(user)


@router.get("/info")
async def get_user_info(
    _: LoginRequired, db: DbSessionDep, user_id: UUID = Query()
) -> UserInfoResponse:
    user = (await db.exec(select(DBUser).where(DBUser.id == user_id))).one()
    return UserInfoResponse.model_validate(user)
