from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Query

from app.api.deps import (
    DbSessionDep,
    LoginRequired,
    RequireRoles,
    SpeedLimReqDep,
    UserServiceDep,
)
from app.exceptions import APIException, ValidationException
from app.models.db.user import UserRole
from app.models.dto.code import BusinessCode
from app.models.dto.request import UserRegisterSubmit
from app.models.dto.response import (
    SelfInfoResponse,
    UnifiedResponse,
    UserCreateResponse,
    UserInfoResponse,
)
from app.utils.response import ResponseBuilder

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
) -> UnifiedResponse[Literal["ok", "conflict", "invalid"]]:
    """检查用户信息可用性"""
    status = await user_service.check_userinfo_availability(field, value)
    return ResponseBuilder.success(data=status)


@router.post(
    "/users",
    summary="用户注册",
    status_code=201,
)
async def create_user(
    user_service: UserServiceDep,
    submit: UserRegisterSubmit = Body(),
    _: Any = SpeedLimReqDep,
) -> UnifiedResponse[UserCreateResponse]:
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
            from app.exceptions import APIException
            from app.models.dto.code import BusinessCode

            if status == "conflict":
                if field == "username":
                    raise APIException(
                        status_code=409,
                        code=BusinessCode.USERNAME_ALREADY_EXISTS,
                        message=f"用户名已存在: {value}",
                    )
                elif field == "email":
                    raise APIException(
                        status_code=409,
                        code=BusinessCode.EMAIL_ALREADY_EXISTS,
                        message=f"邮箱已存在: {value}",
                    )
                elif field == "nickname":
                    raise APIException(
                        status_code=409,
                        code=BusinessCode.NICKNAME_ALREADY_EXISTS,
                        message=f"昵称已存在: {value}",
                    )
            elif status == "invalid":
                if field == "username":
                    raise APIException(
                        status_code=400,
                        code=BusinessCode.USERNAME_INVALID,
                        message=f"用户名格式无效: {value}",
                    )
                elif field == "email":
                    raise APIException(
                        status_code=400,
                        code=BusinessCode.EMAIL_INVALID,
                        message=f"邮箱格式无效: {value}",
                    )
                elif field == "nickname":
                    raise APIException(
                        status_code=400,
                        code=BusinessCode.NICKNAME_INVALID,
                        message=f"昵称格式无效: {value}",
                    )

            # 默认回退
            raise ValidationException(
                message=f"用户信息不可用: {field}: `{value}` ({status})"
            )

    user = await user_service.create_user(
        username=submit.username,
        email=submit.email,
        password=submit.password,
        nickname=submit.nickname,
        role=UserRole.USER,
    )
    return ResponseBuilder.created(
        data=UserCreateResponse.model_validate(user, from_attributes=True),
        message="用户注册成功",
    )


@router.get(
    "/users/me",
    summary="获取当前用户信息",
)
async def get_current_user(
    login_session: LoginRequired,
    user_service: UserServiceDep,
) -> UnifiedResponse[SelfInfoResponse]:
    """获取当前用户信息"""
    user = await user_service.query_user(user_id=login_session.user_id)
    if user is None:
        raise APIException(
            status_code=404, code=BusinessCode.USER_NOT_FOUND, message="用户不存在"
        )
    return ResponseBuilder.success(
        data=SelfInfoResponse.model_validate(user, from_attributes=True)
    )


@router.get(
    "/users/{user_id}",
    summary="获取指定用户信息",
)
async def get_user_by_id(
    _: LoginRequired,
    user_service: UserServiceDep,
    user_id: UUID,
) -> UnifiedResponse[UserInfoResponse]:
    """获取指定用户信息"""
    user = await user_service.query_user(user_id=user_id)
    if user is None:
        raise APIException(
            status_code=404, code=BusinessCode.USER_NOT_FOUND, message="用户不存在"
        )
    return ResponseBuilder.success(
        data=UserInfoResponse.model_validate(user, from_attributes=True)
    )


@router.delete(
    "/users/{user_id}",
    summary="删除用户",
    status_code=200,
)
async def delete_user(
    db: DbSessionDep,
    user_id: UUID,
    _: UserRole = RequireRoles(UserRole.ADMIN, UserRole.SU),
) -> UnifiedResponse[str]:
    """删除用户"""
    raise NotImplementedError
