from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException

from app.api.deps import DbSessionDep, LoginRequired, SpeedLimReqDep
from app.schemas.request import LoginByEmailSubmit, LoginByUsernameSubmit

router = APIRouter(tags=["session"])


@router.post("/login")
async def login(
    db: DbSessionDep,
    submit: LoginByUsernameSubmit | LoginByEmailSubmit = Body(),
    authorization: str = Header(""),
    _: Any = SpeedLimReqDep,
) -> None:
    # 关于类型标注成 Any 的原因:
    # https://github.com/fastapi/fastapi/issues/10127
    if authorization:
        raise HTTPException(409, "需要先退出登录")

    raise NotImplementedError


@router.post("/logout")
async def exit_login(
    login_session: LoginRequired, db: DbSessionDep, _: Any = SpeedLimReqDep
) -> None:
    raise NotImplementedError


@router.post("/refresh")
async def refresh_access_token(
    login_session: LoginRequired, db: DbSessionDep, _: Any = SpeedLimReqDep
) -> None:
    raise NotImplementedError


@router.post("/list")
async def list_session(
    login_session: LoginRequired, db: DbSessionDep, _: Any = SpeedLimReqDep
) -> None:
    raise NotImplementedError
