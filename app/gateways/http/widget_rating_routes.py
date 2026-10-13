"""The thumbs website chat visitors give its answers (public, no bearer token)."""

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
from app.schemas.dto.channels.widget_ratings import (
    WidgetRatingCommand,
    WidgetRatingRequest,
    WidgetRatingView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId

WIDGET_RATING_PATH: str = "/v1/widget/{business_id}/rating"
read_widget_rating_body = build_json_body_dependency(WidgetRatingRequest)


def build_widget_rating_router(
    rate_widget_conversation_operator: OperatorContract[
        WidgetRatingCommand, WidgetRatingView
    ],
    widget_origin_guard: WidgetOriginGuard | None = None,
) -> APIRouter:
    """
    Routes (public; the visitor is the body's session key):
        POST /v1/widget/{business_id}/rating
            Thumbs up or down on the visitor's own chat (an answer named by
            `message_id`, else the latest one), with an optional reason for
            a bad one. Refused to a website the business does not allow
            (403); limited per visitor and network (429).
    """

    router: APIRouter = APIRouter(
        tags=["channels"], responses=standard_error_responses()
    )
    guarded = [] if widget_origin_guard is None else [Depends(widget_origin_guard)]

    @router.options(WIDGET_RATING_PATH, include_in_schema=False)
    def allow_widget_rating_preflight(business_id: str) -> Response:
        del business_id
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers=WIDGET_CORS_HEADERS,
        )

    @router.post(
        WIDGET_RATING_PATH,
        openapi_extra=describe_json_body(WidgetRatingRequest),
        dependencies=guarded,
    )
    def rate_widget_conversation(
        request: Request,
        business_id: str,
        response: Response,
        body: Annotated[WidgetRatingRequest, Depends(read_widget_rating_body)],
    ) -> WidgetRatingView:
        response.headers.update(WIDGET_CORS_HEADERS)
        return rate_widget_conversation_operator.operate(
            WidgetRatingCommand(
                business_id=parse_path_identifier(business_id, BusinessId, "Chat"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
