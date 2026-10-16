"""The landing page's sandbox demos (public, rate limited)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import (
    negotiate_language,
    parse_language_parameter,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.schemas.dto.public_demo import (
    PublicDemoList,
    PublicDemoListQuery,
    PublicDemoMessageCommand,
    PublicDemoMessageRequest,
    PublicDemoReply,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.cldr_language_names import ENGLISH_LOCALE_IDENTIFIER

type ListPublicDemosOperator = OperatorContract[PublicDemoListQuery, PublicDemoList]
type PublicDemoMessageOperator = OperatorContract[
    PublicDemoMessageCommand, PublicDemoReply
]

read_demo_message = build_json_body_dependency(PublicDemoMessageRequest)


def build_public_demo_router(
    list_public_demos_operator: ListPublicDemosOperator,
    public_demo_message_operator: PublicDemoMessageOperator,
) -> APIRouter:
    """
    Routes (no token):
        GET  /v1/public-demos?language=          the demo businesses
        POST /v1/public-demos/{business_id}/messages
                                 a visitor's message; the sandbox answer

    Only the businesses of PUBLIC_DEMO_BUSINESS_IDS answer (any other id is
    404). Every turn is a sandbox turn, and messages are limited per
    conversation, network, demo and for the whole site (429 Retry-After).
    """

    router = APIRouter(tags=["public-demos"], responses=standard_error_responses())

    @router.get("/v1/public-demos")
    def list_public_demos(
        request: Request,
        language: str | None = None,
    ) -> PublicDemoList:
        return list_public_demos_operator.operate(
            PublicDemoListQuery(language=demo_language(request, language))
        )

    @router.post(
        "/v1/public-demos/{business_id}/messages",
        openapi_extra=describe_json_body(PublicDemoMessageRequest),
    )
    def send_public_demo_message(
        request: Request,
        business_id: str,
        body: Annotated[PublicDemoMessageRequest, Depends(read_demo_message)],
    ) -> PublicDemoReply:
        return public_demo_message_operator.operate(
            PublicDemoMessageCommand(
                business_id=parse_path_identifier(business_id, BusinessId, "Demo"),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router


def demo_language(request: Request, raw_language: str | None) -> LanguageTag:
    """`?language=`, else the browser's preferred language, else English."""

    return (
        parse_language_parameter(raw_language)
        or negotiate_language(request.headers.get("accept-language"))
        or LanguageTag(ENGLISH_LOCALE_IDENTIFIER)
    )
