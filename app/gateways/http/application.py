"""FastAPI application assembly: routers, errors, CORS, request ids, health."""

import uuid
from collections.abc import Awaitable, Callable, Sequence

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.contracts.observability import ErrorReportingFacilitatorContract
from app.gateways.http.error_responses import install_error_handlers
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl

REQUEST_ID_HEADER: str = "X-Request-ID"
MAX_REQUEST_ID_LENGTH: int = 128
API_TITLE: str = "Assistant Workshop API"
API_VERSION: str = "0.1.0"


def build_http_application(
    routers: Sequence[APIRouter],
    error_reporter: ErrorReportingFacilitatorContract,
    cors_allowed_origins: Sequence[PublicBaseUrl],
) -> FastAPI:
    """
    Build the HTTP application.

    Application errors map to their status codes; anything else becomes a 500
    without internals and is sent to the error reporter. Every response carries
    an X-Request-ID (taken from the request when present).
    """

    http_application = FastAPI(title=API_TITLE, version=API_VERSION)
    install_error_handlers(http_application)

    async def handle_unexpected_error(request: Request, error: Exception) -> Response:
        del request
        error_reporter.capture_exception(error)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Unexpected server error.",
            },
        )

    http_application.add_exception_handler(Exception, handle_unexpected_error)

    if cors_allowed_origins:
        http_application.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin).rstrip("/") for origin in cors_allowed_origins],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        )

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
