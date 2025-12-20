"""统一的异常定义"""

from typing import Any

from fastapi import HTTPException, status

from app.models.dto.code import BusinessCode


class APIException(HTTPException):
    """统一的API异常类

    用于在业务逻辑中抛出标准化的异常，会被全局异常处理器捕获
    并转换为统一的响应格式。
    """

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: int | BusinessCode = BusinessCode.BAD_REQUEST,
        message: str = "请求参数错误",
        data: Any = None,
    ) -> None:
        """
        初始化API异常

        Args:
            status_code: HTTP状态码
            code: 业务状态码，可以是BusinessCode枚举或整数
            message: 错误消息
            data: 额外的错误数据
        """
        super().__init__(status_code=status_code, detail=message)
        self.code = code.value if isinstance(code, BusinessCode) else code
        self.data = data


class ValidationException(APIException):
    """数据验证异常"""

    def __init__(self, message: str = "数据验证失败", data: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=BusinessCode.VALIDATION_ERROR,
            message=message,
            data=data,
        )


class NotFoundException(APIException):
    """资源未找到异常"""

    def __init__(self, message: str = "资源未找到", data: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code=BusinessCode.NOT_FOUND,
            message=message,
            data=data,
        )


class UnauthorizedException(APIException):
    """未授权异常"""

    def __init__(self, message: str = "未授权访问", data: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=BusinessCode.UNAUTHORIZED,
            message=message,
            data=data,
        )


class ForbiddenException(APIException):
    """权限不足异常"""

    def __init__(self, message: str = "权限不足", data: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code=BusinessCode.FORBIDDEN,
            message=message,
            data=data,
        )


class ConflictException(APIException):
    """资源冲突异常"""

    def __init__(self, message: str = "资源已存在", data: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code=BusinessCode.CONFLICT,
            message=message,
            data=data,
        )


class DatabaseException(APIException):
    """数据库操作异常"""

    def __init__(self, message: str = "数据库操作失败", data: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=BusinessCode.DATABASE_ERROR,
            message=message,
            data=data,
        )


class InternalException(APIException):
    """内部服务器异常"""

    def __init__(self, message: str = "服务器内部错误", data: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=BusinessCode.INTERNAL_ERROR,
            message=message,
            data=data,
        )
