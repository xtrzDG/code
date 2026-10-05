"""FastAPI application assembly: routers, errors, CORS, request ids, health."""

from collections.abc import Sequence

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.types import Lifespan

from app.contracts.observability import ErrorReportingFacilitatorContract
from app.gateways.http.cabinet_cors_middleware import CabinetCorsMiddleware
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.middleware.anonymous_request_limit_middleware import (
    AdmitRequest,
    AnonymousRequestLimitMiddleware,
)
from app.gateways.http.middleware.body_size_limit_middleware import (
    BodySizeLimitMiddleware,
)
from app.gateways.http.middleware.security_headers_middleware import (
    SecurityHeadersMiddleware,
    with_security_headers,
)
from app.gateways.http.request_context_middleware import (
    REQUEST_ID_HEADER,
    RequestContextMiddleware,
    sanitize_request_id,
)
from app.gateways.http.widget_cors_middleware import (
    WIDGET_CORS_HEADERS,
    WidgetCorsMiddleware,
    is_widget_path,
)
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.dto.observability import LogContext
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.utilities.observability.log_context import log_context_of_error

__all__ = ["REQUEST_ID_HEADER", "build_http_application", "sanitize_request_id"]

API_TITLE: str = "Assistant Workshop API"
API_VERSION: str = "0.1.0"


def build_http_application(
    routers: Sequence[APIRouter],
    error_reporter: ErrorReportingFacilitatorContract,
    cors_allowed_origins: Sequence[PublicBaseUrl],
    lifespan: Lifespan[FastAPI] | None = None,
    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT,
    anonymous_request_admission: AdmitRequest | None = None,
) -> FastAPI:
    """
    Build the HTTP application.

    Application errors map to their status codes; anything else becomes a 500
    without internals and is sent to the error reporter with the request,
    business and conversation it happened in. Every response carries an
    X-Request-ID (taken from the request when present), which every log line
    of the request carries too. CORS allows the cabinet origins; the public
    widget routes answer CORS themselves. `GET /healthz` is pure liveness: an
    async handler that needs no request thread, so it answers while slow
    requests hold all of them. `lifespan` runs startup and shutdown work (see
    `app.main`). Request bodies are limited per route (413), every answer
    carries the security headers, and in production the API description
    (/docs, /openapi.json) is not served and HSTS is sent. With
    `anonymous_request_admission`, requests without a token count against
    their client network's generic limit (429 with Retry-After).
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
        headers: dict[str, str] = (
            dict(WIDGET_CORS_HEADERS) if is_widget_path(request.url.path) else {}
        )
        context: LogContext = log_context_of_error(error)
        if context.request_id is not None:
            headers[REQUEST_ID_HEADER] = str(context.request_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Unexpected server error.",
            },
            headers=headers,
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

    if anonymous_request_admission is not None:
        http_application.add_middleware(
            AnonymousRequestLimitMiddleware, admit=anonymous_request_admission
        )

    http_application.add_middleware(WidgetCorsMiddleware)
    # Outside every layer but the security headers, so the request id is
    # bound before anything else runs.
    http_application.add_middleware(RequestContextMiddleware)

    @http_application.get("/healthz", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in routers:
        http_application.include_router(router)

    # Outermost: answers of every other layer get the headers too.
    http_application.add_middleware(
        SecurityHeadersMiddleware, is_https_only=is_production
    )
    return http_application
