import logging
import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError

from app.api.v1.auth import router as auth_router
from app.api.v1.bookings import router as bookings_router
from app.api.v1.specialists import router as specialists_router
from app.api.v1.users import router as users_router
from app.core.exceptions import http_exception_handler, validation_exception_handler
from app.core.logging import setup_logging
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY, render_metrics
from app.core.request_context import request_id_ctx_var

app = FastAPI(title="Booking API", version="0.1.0")
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
setup_logging()
logger = logging.getLogger("app.request")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(specialists_router)
app.include_router(bookings_router)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    token = request_id_ctx_var.set(request_id)
    start = time.perf_counter()
    path = request.url.path
    method = request.method
    try:
        response = await call_next(request)
    except Exception:
        elapsed = time.perf_counter() - start
        REQUEST_COUNT.labels(method=method, path=path, status_code=500).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
        logger.exception(
            "request_failed method=%s path=%s status=500 duration_ms=%.2f",
            method,
            path,
            elapsed * 1000,
        )
        request_id_ctx_var.reset(token)
        raise

    elapsed = time.perf_counter() - start
    REQUEST_COUNT.labels(method=method, path=path, status_code=response.status_code).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%.2f",
        method,
        path,
        response.status_code,
        elapsed * 1000,
    )
    request_id_ctx_var.reset(token)
    return response


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", tags=["observability"])
def metrics() -> Response:
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
