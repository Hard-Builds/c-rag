import sys
import traceback
from typing import Any, Callable, Coroutine

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.responses import JSONResponse

from app.constants import REQUEST_VALIDATION_ERROR
from app.core.custom_exceptions import CustomException
from app.api.models import BaseResponse


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "message": exc.detail},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": status.HTTP_500_INTERNAL_SERVER_ERROR, "message": str(exc)},
    )


async def custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, CustomException):
        return JSONResponse(
            status_code=exc.status,
            content=BaseResponse(
                status=exc.status, message=exc.message, payload={}
            ).model_dump(),
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": status.HTTP_500_INTERNAL_SERVER_ERROR, "message": str(exc)},
    )


def get_generic_exception_handler(
    logger: Any,
) -> Callable[[Request, Exception], Coroutine[Any, Any, JSONResponse]]:
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            content={
                "status": getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
                "detail": getattr(exc, "detail", "An unexpected error occurred."),
            },
        )

    return generic_exception_handler


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "message": REQUEST_VALIDATION_ERROR,
                "payload": {"detail": exc.errors()},
            },
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": status.HTTP_500_INTERNAL_SERVER_ERROR, "message": str(exc)},
    )


def exception_handler(
    exception: Exception, is_raise: bool = False, logger: Any = None
) -> None:
    exc_type, _, tb = sys.exc_info()
    if tb is None:
        if logger:
            logger.error(f"Exception occurred but no traceback available: {exception}")
        if is_raise:
            raise exception
        return

    f = tb.tb_frame
    line_no, filename, function_name = (
        tb.tb_lineno,
        f.f_code.co_filename,
        f.f_code.co_name,
    )
    source_raise = (
        f"Exception type: {exc_type}, "
        f"Exception message: {exception}, "
        f"Filename: {filename}, "
        f"Function: {function_name}, "
        f"Line: {line_no}, "
        f"Stack: {repr(traceback.format_exc())}"
    )
    if logger:
        logger.error(f"{getattr(exception, 'detail', '')} :: {source_raise}")

    if is_raise:
        raise HTTPException(
            status_code=getattr(exception, "status_code", 500),
            detail=getattr(exception, "detail", str(exception)),
        )
