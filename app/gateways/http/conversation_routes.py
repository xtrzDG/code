"""Conversation feed and the owner's test chat (cabinet, concept section 8)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.conversation_feed import (
    ConversationDetailView,
    ConversationListQuery,
    ConversationQuery,
    ConversationSummaryView,
    OwnerTestChatCommand,
    OwnerTestChatRequest,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IncludeSandboxConversations
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.users.prefixed_id import UserId

read_test_chat_body = build_json_body_dependency(OwnerTestChatRequest)
TRUE_FLAGS: frozenset[str] = frozenset({"1", "true", "yes"})
FALSE_FLAGS: frozenset[str] = frozenset({"0", "false", "no"})


def build_conversation_router(
    list_conversations_operator: OperatorContract[
        ConversationListQuery,
        list[ConversationSummaryView],
    ],
    get_conversation_operator: OperatorContract[
        ConversationQuery,
        ConversationDetailView,
    ],
    owner_test_chat_operator: OperatorContract[OwnerTestChatCommand, AssistantReply],
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (all require a bearer token; owners and staff):
        GET  /v1/businesses/{business_id}/conversations?channel=&include_sandbox=
                                                    feed, newest first
        GET  /v1/businesses/{business_id}/conversations/{conversation_id}
                                                    card with messages (audited)
        POST /v1/businesses/{business_id}/test-chat
                                                    {text, session_key?,
                                                     assistant_version_id?}
    """

    router = APIRouter(tags=["conversations"])

    @router.get("/v1/businesses/{business_id}/conversations")
    def list_conversations(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        channel: str | None = None,
        include_sandbox: str | None = None,
    ) -> list[ConversationSummaryView]:
        return list_conversations_operator.operate(
            ConversationListQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                channel=parse_channel(channel),
                include_sandbox=parse_include_sandbox(include_sandbox),
            )
        )

    @router.get("/v1/businesses/{business_id}/conversations/{conversation_id}")
    def get_conversation(
        request: Request,
        business_id: str,
        conversation_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ConversationDetailView:
        return get_conversation_operator.operate(
            ConversationQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                conversation_id=parse_path_identifier(
                    conversation_id,
                    ConversationId,
                    "Conversation",
                ),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/test-chat",
        openapi_extra=describe_json_body(OwnerTestChatRequest),
    )
    def owner_test_chat(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[OwnerTestChatRequest, Depends(read_test_chat_body)],
    ) -> AssistantReply:
        return owner_test_chat_operator.operate(
            OwnerTestChatCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
            )
        )

    return router


def parse_channel(raw_channel: str | None) -> ChannelKind | None:
    if raw_channel is None or raw_channel.strip() == "":
        return None

    try:
        return ChannelKind(raw_channel.strip().lower())
    except ValueError as error:
        known_channels: str = ", ".join(kind.value for kind in ChannelKind)
        raise ValidationFailedError(
            f"channel must be one of: {known_channels}."
        ) from error


def parse_include_sandbox(raw_flag: str | None) -> IncludeSandboxConversations:
    if raw_flag is None:
        return False

    flag: str = raw_flag.strip().lower()
    if flag in TRUE_FLAGS:
        return True

    if flag in FALSE_FLAGS:
        return False

    raise ValidationFailedError("include_sandbox must be true or false.")
