from typing import Any

from fastapi import APIRouter, Body, Header

from app.api.deps import AuthServiceDep, LoginRequired, SpeedLimReqDep
from app.exceptions import APIException
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
from app.utils.response import ResponseUtil

router = APIRouter(tags=["auth"])


@router.post(
    "/login",
    summary="用户登录",
    description="支持通过用户名、邮箱或用户ID登录",
)
async def login(
    auth_service: AuthServiceDep,
    submit: LoginByUsernameSubmit | LoginByEmailSubmit | LoginByUserIdSubmit = Body(),
    authorization: str = Header(""),
    _: Any = SpeedLimReqDep,
) -> ApiResponse[LoginSuccessResponse]:
    """用户登录"""
    if authorization:
        return ResponseUtil.unauthorized(message="需要先退出登录")

    params: dict[str, Any] = {"password": submit.password}
    if isinstance(submit, LoginByEmailSubmit):
        params["email"] = submit.email
    elif isinstance(submit, LoginByUsernameSubmit):
        params["username"] = submit.username
    elif isinstance(submit, LoginByUserIdSubmit):
        params["user_id"] = submit.user_id

    result = await auth_service.login(**params)
    if result is None:
        raise APIException(
            status_code=401, code=BusinessCode.LOGIN_FAILED, message="用户名或密码错误"
        )

    access_token, refresh_token = result
    return ResponseUtil.success(
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
    login_session: LoginRequired,
    auth_service: AuthServiceDep,
    _: Any = SpeedLimReqDep,
) -> ApiResponse[str]:
    """用户登出"""
    if await auth_service.logout(access_token=login_session.access_token):
        return ResponseUtil.success(data="ok", message="登出成功")

    return ResponseUtil.bad_request(message="登出失败")


@router.post(
    "/refresh",
    summary="刷新访问令牌",
    description="使用刷新令牌获取新的访问令牌",
)
async def refresh_token(
    login_session: LoginRequired,
    auth_service: AuthServiceDep,
    _: Any = SpeedLimReqDep,
    submit: RefreshTokenSubmit = Body(),
) -> ApiResponse[RefreshTokenResponse]:
    """刷新访问令牌"""
    result = await auth_service.refresh_access_token(
        access_token=login_session.access_token,
        refresh_token=submit.refresh_token,
    )

    if result is None:
        raise APIException(
            status_code=401,
            code=BusinessCode.TOKEN_REFRESH_FAILED,
            message="令牌刷新失败",
        )

    new_access_token, new_refresh_token = result
    return ResponseUtil.success(
        data=RefreshTokenResponse(
            access_token=new_access_token, refresh_token=new_refresh_token
        ),
        message="令牌刷新成功",
    )
