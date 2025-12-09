from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.db.problem import ProblemDetails, ProblemType
from app.models.db.user import UserRole

from .base import BaseUser
from .code import BusinessCode

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一的API响应格式"""

    code: int = Field(description="业务状态码")
    message: str = Field(description="响应消息")
    data: T | None = Field(default=None, description="响应数据")
    success: bool = Field(description="是否成功")

    @classmethod
    def ok(cls, data: T | None = None, message: str = "success") -> "ApiResponse[T]":
        """创建成功响应"""
        return cls(code=BusinessCode.SUCCESS, message=message, data=data, success=True)

    @classmethod
    def error(cls, code: int, message: str, data: T | None = None) -> "ApiResponse[T]":
        """创建错误响应"""
        return cls(code=code, message=message, data=data, success=False)

    @classmethod
    def not_found(cls, message: str = "资源未找到") -> "ApiResponse[Any]":
        """创建404响应"""
        return cls.error(BusinessCode.NOT_FOUND, message)

    @classmethod
    def bad_request(cls, message: str = "请求参数错误") -> "ApiResponse[Any]":
        """创建400响应"""
        return cls.error(BusinessCode.BAD_REQUEST, message)

    @classmethod
    def unauthorized(cls, message: str = "未授权") -> "ApiResponse[Any]":
        """创建401响应"""
        return cls.error(BusinessCode.UNAUTHORIZED, message)

    @classmethod
    def forbidden(cls, message: str = "权限不足") -> "ApiResponse[Any]":
        """创建403响应"""
        return cls.error(BusinessCode.FORBIDDEN, message)


# 以下是原有的响应模型，将逐步迁移到新的统一格式
class ProblemResponse(BaseModel):
    id: UUID
    type: ProblemType
    content: str
    explanation: str | None
    details: ProblemDetails


class UserInfoResponse(BaseUser):
    id: UUID


class SelfInfoResponse(UserInfoResponse):
    role: UserRole


class ProblemSetResponse(BaseModel):
    id: UUID
    name: str
    count: int


class ProblemSetCreateStatus:
    SUCCESS = "SUCCESS"
    ALREADY_EXISTS = "ALREADY_EXISTS"


class ProblemSetCreateResponse(BaseModel):
    id: UUID
    status: str


class UserCreateResponse(SelfInfoResponse):
    pass


class RefreshTokenResponse(BaseModel):
    access_token: UUID
    refresh_token: UUID | None = None


class LoginSuccessResponse(BaseModel):
    access_token: UUID
    refresh_token: UUID
