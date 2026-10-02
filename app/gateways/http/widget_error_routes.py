"""The website widget's error beacon: errors of widget.js on businesses' sites."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_client_ip_address,
)
from app.gateways.http.widget_cors_middleware import WIDGET_CORS_HEADERS
from app.schemas.dto.widget_errors import WidgetErrorCommand, WidgetErrorReport

WIDGET_ERRORS_PATH: str = "/v1/widget/errors"

read_widget_error_body = build_json_body_dependency(WidgetErrorReport)


def build_widget_error_router(
    report_widget_error_operator: OperatorContract[WidgetErrorCommand, None],
) -> APIRouter:
    """
    Route (public, no token; CORS for any site like the other widget routes):
        POST /v1/widget/errors    one widget error: kind, phase, error type,
                                  line and column in widget.js; no message
                                  text. 204, or 429 when a network, a
                                  business or the platform reports too many.

    The widget sends it with `navigator.sendBeacon` (text/plain JSON, no
    preflight, no cookies).
    """

    router = APIRouter(tags=["widget"])

    @router.options(WIDGET_ERRORS_PATH, include_in_schema=False)
    def allow_widget_error_preflight() -> Response:
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers=WIDGET_CORS_HEADERS,
        )

    @router.post(
        WIDGET_ERRORS_PATH,
        status_code=status.HTTP_204_NO_CONTENT,
        openapi_extra=describe_json_body(WidgetErrorReport),
    )
    def report_widget_error(
        request: Request,
        body: Annotated[WidgetErrorReport, Depends(read_widget_error_body)],
    ) -> Response:
        report_widget_error_operator.operate(
            WidgetErrorCommand(
                report=body,
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
