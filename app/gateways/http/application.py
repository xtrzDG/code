"""FastAPI application assembly: routers, errors, CORS, request ids, health."""

import uuid
from collections.abc import Awaitable, Callable, Sequence

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.types import Lifespan

from app.contracts.observability import ErrorReportingFacilitatorContract
from app.gateways.http.cabinet_cors_middleware import CabinetCorsMiddleware
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.middleware.body_size_limit_middleware import (
    BodySizeLimitMiddleware,
)
from app.gateways.http.middleware.security_headers_middleware import (
    SecurityHeadersMiddleware,
    with_security_headers,
)
from app.gateways.http.widget_cors_middleware import (
    WIDGET_CORS_HEADERS,
    WidgetCorsMiddleware,
    is_widget_path,
)
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl

REQUEST_ID_HEADER: str = "X-Request-ID"
MAX_REQUEST_ID_LENGTH: int = 128
API_TITLE: str = "Assistant Workshop API"
API_VERSION: str = "0.1.0"


def build_http_application(
    routers: Sequence[APIRouter],
    error_reporter: ErrorReportingFacilitatorContract,
    cors_allowed_origins: Sequence[PublicBaseUrl],
    lifespan: Lifespan[FastAPI] | None = None,
    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT,
) -> FastAPI:
    """
    Build the HTTP application.

    Application errors map to their status codes; anything else becomes a 500
    without internals and is sent to the error reporter. Every response carries
    an X-Request-ID (taken from the request when present). CORS allows the
    cabinet origins; the public widget routes answer CORS themselves.
    `lifespan` runs startup and shutdown work (see `app.main`). Request
    bodies are limited per route (413), every answer carries the security
    headers, and in production the API description (/docs, /openapi.json)
    is not served and HSTS is sent.
    """

    is_production: bool = environment is DeploymentEnvironment.PRODUCTION
    http_application = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        lifespan=lifespan,
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )
    install_error_handlers(http_application)
    # Inside CORS (added below), so a refused body still answers with CORS.
    http_application.add_middleware(BodySizeLimitMiddleware)

    async def handle_unexpected_error(request: Request, error: Exception) -> Response:
        error_reporter.capture_exception(error)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Unexpected server error.",
            },
            headers=(WIDGET_CORS_HEADERS if is_widget_path(request.url.path) else None),
        )

    http_application.add_exception_handler(
        Exception, with_security_headers(handle_unexpected_error, is_production)
    )

    if cors_allowed_origins:
        http_application.add_middleware(
            CabinetCorsMiddleware,
            allow_origins=[str(origin).rstrip("/") for origin in cors_allowed_origins],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        )

    http_application.add_middleware(WidgetCorsMiddleware)

    @http_application.middleware("http")
    async def attach_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id: str = sanitize_request_id(request.headers.get(REQUEST_ID_HEADER))
        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    @http_application.get("/healthz", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in routers:
        http_application.include_router(router)

    # Outermost: answers of every other layer get the headers too.
    http_application.add_middleware(
        SecurityHeadersMiddleware, is_https_only=is_production
    )
    return http_application


def sanitize_request_id(raw_request_id: str | None) -> str:
    """Keep a caller's request id if it is short and printable, else make one."""

    if (
        raw_request_id is not None
        and 0 < len(raw_request_id) <= MAX_REQUEST_ID_LENGTH
        and raw_request_id.isascii()
        and raw_request_id.isprintable()
    ):
        return raw_request_id

    return str(uuid.uuid4())
