"""响应工具类"""

from typing import Any, TypeVar

from app.models.dto.response import ApiResponse
from app.models.dto.code import BusinessCode

T = TypeVar("T")


class ResponseUtil:
    """响应工具类，提供便捷的响应构建方法"""

    @staticmethod
    def success(data: T | None = None, message: str = "success") -> ApiResponse[T]:
        """创建成功响应"""
        return ApiResponse.ok(data=data, message=message)

    @staticmethod
    def created(data: T | None = None, message: str = "创建成功") -> ApiResponse[T]:
        """创建成功响应（201）"""
        return ApiResponse(
            code=BusinessCode.CREATED, message=message, data=data, success=True
        )

    @staticmethod
    def updated(data: T | None = None, message: str = "更新成功") -> ApiResponse[T]:
        """更新成功响应"""
        return ApiResponse(
            code=BusinessCode.UPDATED, message=message, data=data, success=True
        )

    @staticmethod
    def deleted(message: str = "删除成功") -> ApiResponse[str]:
        """删除成功响应"""
        return ApiResponse(
            code=BusinessCode.DELETED, message=message, data=None, success=True
        )

    @staticmethod
    def bad_request(
        message: str = "请求参数错误", data: Any = None
    ) -> ApiResponse[Any]:
        """创建400错误响应"""
        return ApiResponse.error(
            code=BusinessCode.BAD_REQUEST, message=message, data=data
        )

    @staticmethod
    def unauthorized(message: str = "未授权", data: Any = None) -> ApiResponse[Any]:
        """创建401错误响应"""
        return ApiResponse.error(
            code=BusinessCode.UNAUTHORIZED, message=message, data=data
        )

    @staticmethod
    def forbidden(message: str = "权限不足", data: Any = None) -> ApiResponse[Any]:
        """创建403错误响应"""
        return ApiResponse.error(
            code=BusinessCode.FORBIDDEN, message=message, data=data
        )

    @staticmethod
    def not_found(message: str = "资源未找到", data: Any = None) -> ApiResponse[Any]:
        """创建404错误响应"""
        return ApiResponse.error(
            code=BusinessCode.NOT_FOUND, message=message, data=data
        )

    @staticmethod
    def conflict(message: str = "资源冲突", data: Any = None) -> ApiResponse[Any]:
        """创建409错误响应"""
        return ApiResponse.error(code=BusinessCode.CONFLICT, message=message, data=data)

    @staticmethod
    def validation_error(
        message: str = "数据验证失败", data: Any = None
    ) -> ApiResponse[Any]:
        """创建422验证错误响应"""
        return ApiResponse.error(
            code=BusinessCode.VALIDATION_ERROR, message=message, data=data
        )

    @staticmethod
    def internal_error(
        message: str = "服务器内部错误", data: Any = None
    ) -> ApiResponse[Any]:
        """创建500错误响应"""
        return ApiResponse.error(
            code=BusinessCode.INTERNAL_ERROR, message=message, data=data
        )
