from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.request_context import request_id_ctx_var


def _error_payload(code: str, message: str, detail):
    return {
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
        },
        "detail": detail,
        "request_id": request_id_ctx_var.get(),
    }


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            code=f"http_{exc.status_code}",
            message=str(exc.detail),
            detail=exc.detail,
        ),
        headers=exc.headers,
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_payload(
            code="validation_error",
            message="Request validation failed",
            detail=exc.errors(),
        ),
    )
