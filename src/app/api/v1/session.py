from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Header, HTTPException

from app.api.deps import DbSessionDep, LoginRequired, SpeedLimReqDep
from app.db.operations import login, logout, refresh_access_token
from app.schemas.request import LoginByEmailSubmit, LoginByUsernameSubmit
from app.schemas.response import LoginSuccessResponse, RefreshTokenResponse

router = APIRouter(tags=["session"])


@router.post("/login")
async def do_login(
    db: DbSessionDep,
    submit: LoginByUsernameSubmit | LoginByEmailSubmit = Body(),
    authorization: str = Header(""),
    _: Any = SpeedLimReqDep,
) -> LoginSuccessResponse:
    # 关于类型标注成 Any 的原因:
    # https://github.com/fastapi/fastapi/issues/10127
    if authorization:
        raise HTTPException(409, "需要先退出登录")
    params: dict[str, str] = {"password": submit.password}
    if isinstance(submit, LoginByEmailSubmit):
        params["email"] = submit.email
    elif isinstance(submit, LoginByUsernameSubmit):
        params["username"] = submit.username
    if (_ := await login(db, **params)) is None:
        raise HTTPException(401, "用户名或密码错误")
    access_token, refresh_token = _
    return LoginSuccessResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
async def exit_login(
    login_session: LoginRequired, db: DbSessionDep, _: Any = SpeedLimReqDep
) -> Literal["ok"]:
    if await logout(db, login_session.access_token):
        return "ok"
    raise HTTPException(400, "登出失败")


@router.post("/refresh")
async def do_refresh_access_token(
    login_session: LoginRequired,
    db: DbSessionDep,
    _: Any = SpeedLimReqDep,
    refresh_token: UUID = Body(),
) -> RefreshTokenResponse:
    if (
        _ := refresh_access_token(db, login_session.access_token, refresh_token)
    ) is None:
        raise HTTPException(401, "凭据错误")

    new_access_token, new_refresh_token = _
    return RefreshTokenResponse(
        access_token=new_access_token, refresh_token=new_refresh_token
    )
