from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.db.problem import ProblemType, SelectiveProblemDetails

from .base import BaseUser


class BaseProblem(BaseModel):
    content: str


class BaseProblemSet(BaseModel):
    name: str
    description: str = ""
    is_public: bool = False
    tags: list[str] = []


class SelectiveProblemSubmit(BaseProblem):
    type: Literal[ProblemType.SELECTIVE] = ProblemType.SELECTIVE
    details: SelectiveProblemDetails
    tags: list[str] = Field(default_factory=list, description="题目标签")


type ProblemSubmit = SelectiveProblemSubmit  # |...


class ProblemSetSubmit(BaseProblemSet):
    pass


class UserRegisterSubmit(BaseUser):
    password: str


class LoginByUsernameSubmit(BaseModel):
    username: str
    password: str


class LoginByEmailSubmit(BaseModel):
    email: str
    password: str


class LoginByUserIdSubmit(BaseModel):
    user_id: UUID
    password: str


class RefreshTokenSubmit(BaseModel):
    refresh_token: UUID


# Tag相关的请求模型
class TagCreateRequest(BaseModel):
    """创建标签请求模型"""

    name: str = Field(..., min_length=1, max_length=30, description="标签名称")


class TagUpdateRequest(BaseModel):
    """更新标签请求模型"""

    name: str = Field(..., min_length=1, max_length=30, description="新的标签名称")


class TagSearchRequest(BaseModel):
    """标签搜索请求模型"""

    keyword: str | None = Field(None, description="搜索关键词")
    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
