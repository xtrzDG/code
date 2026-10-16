"""The website widget's "Talk to a person" (public, no bearer token)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.widget_cors_middleware import WIDGET_CORS_HEADERS
from app.gateways.http.widget_origin_guard import WidgetOriginGuard
from app.schemas.dto.channels.widget_handoff import (
    WidgetHandoffCommand,
    WidgetHandoffRequest,
    WidgetHandoffView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId

WIDGET_HANDOFF_PATH: str = "/v1/widget/{business_id}/handoff"

read_widget_handoff_body = build_json_body_dependency(WidgetHandoffRequest)


def build_widget_handoff_router(
    widget_handoff_operator: OperatorContract[WidgetHandoffCommand, WidgetHandoffView],
    widget_origin_guard: WidgetOriginGuard | None = None,
) -> APIRouter:
    """
    Routes (public; the visitor is the widget's session key, in the body):
        POST /v1/widget/{business_id}/handoff
            "Talk to a person": the visitor's conversation goes to staff
            (reason customer_request; opened now if the visitor has not
            written yet) and the visitor is told when they hear back.
            Asking again while staff have it changes nothing. Limited like
            the widget's messages (429 with Retry-After), and refused to a
            website the business does not allow (403).
    """

    router: APIRouter = APIRouter(
        tags=["channels"], responses=standard_error_responses()
    )
    guarded = [] if widget_origin_guard is None else [Depends(widget_origin_guard)]

    @router.options(WIDGET_HANDOFF_PATH, include_in_schema=False)
    def allow_widget_handoff_preflight(business_id: str) -> Response:
        del business_id
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers=WIDGET_CORS_HEADERS,
        )

    @router.post(
        WIDGET_HANDOFF_PATH,
        openapi_extra=describe_json_body(WidgetHandoffRequest),
        dependencies=guarded,
    )
    def request_widget_handoff(
        request: Request,
        business_id: str,
        response: Response,
        body: Annotated[WidgetHandoffRequest, Depends(read_widget_handoff_body)],
    ) -> WidgetHandoffView:
        response.headers.update(WIDGET_CORS_HEADERS)
        return widget_handoff_operator.operate(
            WidgetHandoffCommand(
                business_id=parse_path_identifier(business_id, BusinessId, "Chat"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
