from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException

from app.api.deps import DbSessionDep, LoginRequired, SpeedLimReqDep
from app.models.dto.code import BusinessCode
from app.models.dto.request import (
    LoginByEmailSubmit,
    LoginByUserIdSubmit,
    LoginByUsernameSubmit,
    RefreshTokenSubmit,
)
from app.models.dto.response import (
    ApiResponse,
    LoginSuccessResponse,
    RefreshTokenResponse,
)
from app.services.session import session_service

router = APIRouter(tags=["auth"])


@router.post(
    "/login",
    summary="用户登录",
    description="支持通过用户名、邮箱或用户ID登录",
)
async def login(
    db: DbSessionDep,
    submit: LoginByUsernameSubmit | LoginByEmailSubmit | LoginByUserIdSubmit = Body(),
    authorization: str = Header(""),
    _: Any = SpeedLimReqDep,
) -> ApiResponse[LoginSuccessResponse]:
    """用户登录"""
    if authorization:
        return ApiResponse.error(
            code=BusinessCode.ALREADY_LOGGED_IN, message="需要先退出登录"
        )

    params: dict[str, Any] = {"password": submit.password}
    if isinstance(submit, LoginByEmailSubmit):
        params["email"] = submit.email
    elif isinstance(submit, LoginByUsernameSubmit):
        params["username"] = submit.username
    elif isinstance(submit, LoginByUserIdSubmit):
        params["user_id"] = submit.user_id

    result = await session_service.login(db, **params)
    if result is None:
        return ApiResponse.error(
            code=BusinessCode.LOGIN_FAILED, message="用户名或密码错误"
        )

    access_token, refresh_token = result
    return ApiResponse.ok(
        data=LoginSuccessResponse(
            access_token=access_token, refresh_token=refresh_token
        ),
        message="登录成功",
    )


@router.post(
    "/logout",
    summary="用户登出",
    description="用户主动登出，使当前访问令牌失效",
)
async def logout(
    login_session: LoginRequired, db: DbSessionDep, _: Any = SpeedLimReqDep
) -> ApiResponse[str]:
    """用户登出"""
    if await session_service.logout(db, login_session.access_token):
        return ApiResponse.ok(data="ok", message="登出成功")

    return ApiResponse.error(code=BusinessCode.LOGOUT_FAILED, message="登出失败")


@router.post(
    "/refresh",
    summary="刷新访问令牌",
    description="使用刷新令牌获取新的访问令牌",
)
async def refresh_token(
    login_session: LoginRequired,
    db: DbSessionDep,
    _: Any = SpeedLimReqDep,
    submit: RefreshTokenSubmit = Body(),
) -> ApiResponse[RefreshTokenResponse]:
    """刷新访问令牌"""
    result = await session_service.refresh_access_token(
        db,
        login_session.access_token,
        submit.refresh_token,
    )

    if result is None:
        return ApiResponse.error(
            code=BusinessCode.TOKEN_REFRESH_FAILED, message="凭据错误"
        )

    new_access_token, new_refresh_token = result
    return ApiResponse.ok(
        data=RefreshTokenResponse(
            access_token=new_access_token, refresh_token=new_refresh_token
        ),
        message="令牌刷新成功",
    )
