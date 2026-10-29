"""Production quality: a client's trend for the admin, a conversation's score."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import parse_path_identifier
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.admin import AdminClientQuery
from app.schemas.dto.quality import (
    ClientQualityView,
    ConversationQualityQuery,
    ConversationQualityView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.users.prefixed_id import UserId


def build_quality_router(
    current_user: CurrentUserDependency,
    get_client_quality: OperatorContract[AdminClientQuery, ClientQualityView],
    get_conversation_quality: OperatorContract[
        ConversationQualityQuery, ConversationQualityView
    ],
) -> APIRouter:
    """
    Routes (bearer token):
        GET /v1/admin/clients/{business_id}/quality
                the judge's daily averages of the client's real
                conversations, 30 days, and the lowest scores (platform
                admin; scores only, not audited)
        GET /v1/businesses/{business_id}/conversations/{conversation_id}/quality
                the conversation's score and the judge's notes; no score
                when the nightly sample did not pick it (owners and staff)
    """

    router = APIRouter(tags=["quality"], responses=standard_error_responses())

    @router.get("/v1/admin/clients/{business_id}/quality")
    def get_client_quality_route(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ClientQualityView:
        return get_client_quality.operate(
            AdminClientQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.get("/v1/businesses/{business_id}/conversations/{conversation_id}/quality")
    def get_conversation_quality_route(
        business_id: str,
        conversation_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ConversationQualityView:
        return get_conversation_quality.operate(
            ConversationQualityQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                conversation_id=parse_path_identifier(
                    conversation_id, ConversationId, "Conversation"
                ),
            )
        )

    return router
