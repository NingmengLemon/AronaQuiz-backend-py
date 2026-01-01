"""响应工具类"""

from typing_extensions import Any, TypeVar

from app.models.dto.code import BusinessCode
from app.models.dto.response import UnifiedResponse

T = TypeVar("T")


class ResponseBuilder:
    """响应工具类，提供便捷的响应构建方法"""

    @classmethod
    def success(
        cls, data: T | None = None, message: str = "success"
    ) -> UnifiedResponse[T]:
        """创建成功响应"""
        return UnifiedResponse.ok(data=data, message=message)

    @classmethod
    def created(
        cls, data: T | None = None, message: str = "创建成功"
    ) -> UnifiedResponse[T]:
        """创建成功响应（201）"""
        return UnifiedResponse(
            code=BusinessCode.CREATED, message=message, data=data, success=True
        )

    @classmethod
    def updated(
        cls, data: T | None = None, message: str = "更新成功"
    ) -> UnifiedResponse[T]:
        """更新成功响应"""
        return UnifiedResponse(
            code=BusinessCode.UPDATED, message=message, data=data, success=True
        )

    @classmethod
    def deleted(cls, message: str = "删除成功") -> UnifiedResponse[str]:
        """删除成功响应"""
        return UnifiedResponse(
            code=BusinessCode.DELETED, message=message, data=None, success=True
        )

    @classmethod
    def bad_request(
        cls, message: str = "请求参数错误", data: Any = None
    ) -> UnifiedResponse[Any]:
        """创建400错误响应"""
        return UnifiedResponse.error(
            code=BusinessCode.BAD_REQUEST, message=message, data=data
        )

    @classmethod
    def unauthorized(
        cls, message: str = "未授权", data: Any = None
    ) -> UnifiedResponse[Any]:
        """创建401错误响应"""
        return UnifiedResponse.error(
            code=BusinessCode.UNAUTHORIZED, message=message, data=data
        )

    @classmethod
    def forbidden(
        cls, message: str = "权限不足", data: Any = None
    ) -> UnifiedResponse[Any]:
        """创建403错误响应"""
        return UnifiedResponse.error(
            code=BusinessCode.FORBIDDEN, message=message, data=data
        )

    @classmethod
    def not_found(
        cls, message: str = "资源未找到", data: Any = None
    ) -> UnifiedResponse[Any]:
        """创建404错误响应"""
        return UnifiedResponse.error(
            code=BusinessCode.NOT_FOUND, message=message, data=data
        )

    @classmethod
    def conflict(
        cls, message: str = "资源冲突", data: Any = None
    ) -> UnifiedResponse[Any]:
        """创建409错误响应"""
        return UnifiedResponse.error(
            code=BusinessCode.CONFLICT, message=message, data=data
        )

    @classmethod
    def validation_error(
        cls, message: str = "数据验证失败", data: Any = None
    ) -> UnifiedResponse[Any]:
        """创建422验证错误响应"""
        return UnifiedResponse.error(
            code=BusinessCode.VALIDATION_ERROR, message=message, data=data
        )

    @classmethod
    def internal_error(
        cls, message: str = "服务器内部错误", data: Any = None
    ) -> UnifiedResponse[Any]:
        """创建500错误响应"""
        return UnifiedResponse.error(
            code=BusinessCode.INTERNAL_ERROR, message=message, data=data
        )
