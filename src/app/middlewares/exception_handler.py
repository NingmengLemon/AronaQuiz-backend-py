"""统一的异常处理中间件"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic_core import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import APIException
from app.models.dto.code import BusinessCode
from app.models.dto.response import ApiResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(APIException)
    async def api_exception_handler(
        request: Request, exc: APIException
    ) -> JSONResponse:
        """处理自定义API异常"""
        logger.error(f"API异常: {exc.detail}, 路径: {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse.error(
                code=exc.code, message=str(exc.detail), data=exc.data
            ).model_dump(mode="json"),
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """处理Pydantic验证异常"""
        logger.error(f"验证异常: {exc.errors()}, 路径: {request.url.path}")
        return JSONResponse(
            status_code=422,
            content=ApiResponse.error(
                code=BusinessCode.VALIDATION_ERROR,
                message="数据验证失败",
                data=exc.errors(),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        """处理数据库异常"""
        logger.error(f"数据库异常: {str(exc)}, 路径: {request.url.path}")
        return JSONResponse(
            status_code=500,
            content=ApiResponse.error(
                code=BusinessCode.DATABASE_ERROR, message="数据库操作失败"
            ).model_dump(mode="json"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """处理HTTP异常"""
        logger.error(
            f"HTTP异常: {exc.detail}, 状态码: {exc.status_code}, 路径: {request.url.path}"
        )

        # 检查是否是APIException（已包含业务码）
        if isinstance(exc, APIException):
            return JSONResponse(
                status_code=exc.status_code,
                content=ApiResponse.error(
                    code=exc.code, message=str(exc.detail), data=exc.data
                ).model_dump(mode="json"),
            )

        # 检查detail是否已经是ApiResponse格式（包含code）
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            # 使用detail中指定的特定业务错误码
            code_value = exc.detail.get("code")
            if isinstance(code_value, int):
                code = code_value
            elif isinstance(code_value, BusinessCode):
                code = code_value.value
            else:
                code = (
                    int(code_value)
                    if code_value is not None
                    else BusinessCode.INTERNAL_ERROR.value
                )

            message = str(exc.detail.get("message", str(exc.detail)))
            data = exc.detail.get("data")
        else:
            # 映射HTTP状态码到通用业务码
            status_code_map = {
                400: BusinessCode.BAD_REQUEST,
                401: BusinessCode.UNAUTHORIZED,
                403: BusinessCode.FORBIDDEN,
                404: BusinessCode.NOT_FOUND,
                422: BusinessCode.VALIDATION_ERROR,
                500: BusinessCode.INTERNAL_ERROR,
            }
            code_obj = status_code_map.get(exc.status_code, BusinessCode.INTERNAL_ERROR)
            code = code_obj.value
            message = str(exc.detail)
            data = None

        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse.error(code=code, message=message, data=data).model_dump(
                mode="json"
            ),  # 使用mode='json'确保UUID等类型被正确序列化
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """处理未捕获的异常"""
        logger.error(f"未捕获异常: {str(exc)}, 路径: {request.url.path}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ApiResponse.error(
                code=BusinessCode.INTERNAL_ERROR, message="服务器内部错误"
            ).model_dump(mode="json"),
        )
