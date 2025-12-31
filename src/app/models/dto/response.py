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

    code: int = Field(description="状态码")
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


# Tag相关的响应模型
class TagResponse(BaseModel):
    """标签响应模型"""

    id: UUID
    name: str


class TagDetailResponse(TagResponse):
    """标签详情响应模型"""

    problem_count: int = 0
    problemset_count: int = 0


class TagCreateResponse(BaseModel):
    """标签创建响应模型"""

    id: UUID
    name: str
    message: str = "标签创建成功"


class TagUpdateResponse(BaseModel):
    """标签更新响应模型"""

    id: UUID
    old_name: str
    new_name: str
    message: str = "标签更新成功"


class TagListResponse(BaseModel):
    """标签列表响应模型"""

    tags: list[TagResponse]
    total: int
    page: int
    page_size: int


class TagProblemResponse(BaseModel):
    """标签关联的题目响应模型"""

    id: UUID
    content: str
    type: ProblemType
    problemset_id: UUID


class TagProblemSetResponse(BaseModel):
    """标签关联的题目集响应模型"""

    id: UUID
    name: str
    description: str | None
    is_public: bool
    owner_id: UUID


class TagProblemsResponse(BaseModel):
    """标签关联题目列表响应模型"""

    tag: TagResponse
    problems: list[TagProblemResponse]
    total: int


class TagProblemSetsResponse(BaseModel):
    """标签关联题目集列表响应模型"""

    tag: TagResponse
    problemsets: list[TagProblemSetResponse]
    total: int
