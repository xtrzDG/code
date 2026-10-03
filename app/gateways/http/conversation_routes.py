"""Conversation feed and the owner's test chat (cabinet, concept section 8)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.byte_ranges import ByteRange, read_byte_range
from app.gateways.http.conversations.feed_query_values import (
    parse_channel,
    parse_include_sandbox,
    parse_local_date,
    parse_search,
    parse_status,
)
from app.gateways.http.conversations.recording_response import (
    RECORDING_OPENAPI_RESPONSES,
    build_recording_response,
)
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.call_recordings import CallRecordingQuery, RecordingAudio
from app.schemas.dto.conversation_feed.conversation_actions import (
    ConversationRatingRequest,
    RateConversationCommand,
    SendStaffMessageCommand,
    StaffMessageRequest,
    StaffMessageResult,
)
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationDetailView,
    ConversationListQuery,
    ConversationMessagesQuery,
    ConversationPage,
    ConversationQuery,
    ConversationSummaryView,
    MessagePage,
)
from app.schemas.dto.conversation_feed.owner_test_chat import (
    OwnerTestChatCommand,
    OwnerTestChatRequest,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.users.prefixed_id import UserId

read_test_chat_body = build_json_body_dependency(OwnerTestChatRequest)
read_rating_body = build_json_body_dependency(ConversationRatingRequest)
read_staff_message_body = build_json_body_dependency(StaffMessageRequest)


def build_conversation_router(
    list_conversations_operator: OperatorContract[
        ConversationListQuery,
        ConversationPage,
    ],
    get_conversation_operator: OperatorContract[
        ConversationQuery,
        ConversationDetailView,
    ],
    owner_test_chat_operator: OperatorContract[OwnerTestChatCommand, AssistantReply],
    rate_conversation_operator: OperatorContract[
        RateConversationCommand,
        ConversationSummaryView,
    ],
    current_user: CurrentUserDependency,
    send_staff_message_operator: OperatorContract[
        SendStaffMessageCommand,
        StaffMessageResult,
    ],
    get_call_recording_operator: OperatorContract[CallRecordingQuery, RecordingAudio],
    list_conversation_messages_operator: OperatorContract[
        ConversationMessagesQuery, MessagePage
    ],
) -> APIRouter:
    """
    Routes (all require a bearer token; owners and staff):
        GET  /v1/businesses/{business_id}/conversations?channel=&status=
             &from=&to=&search=&include_sandbox=&limit=&cursor=
                                                    one page of the feed, the
                                                    latest message first
        GET  /v1/businesses/{business_id}/conversations/{conversation_id}
                                                    card with messages, calls,
                                                    bookings, leads, handoffs
                                                    (audited)
        GET  .../conversations/{conversation_id}/messages?limit=&cursor=
                                                    earlier messages of the
                                                    card, oldest first (audited)
        PUT  .../conversations/{conversation_id}/rating
                                                    {rating: good|bad|null}
        POST .../conversations/{conversation_id}/messages
                                                    {text, as_template?}: staff
                                                    write to the customer
                                                    (audited)
        GET  /v1/businesses/{business_id}/calls/{call_id}/recording
                                                    the call's audio (audited,
                                                    never kept by shared caches)
        POST /v1/businesses/{business_id}/test-chat
                                                    {text, session_key?,
                                                     assistant_version_id?}
    """

    router = APIRouter(tags=["conversations"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/conversations")
    def list_conversations(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        channel: str | None = None,
        status: str | None = None,
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
        search: str | None = None,
        include_sandbox: str | None = None,
        limit: str | None = None,
        cursor: str | None = None,
    ) -> ConversationPage:
        return list_conversations_operator.operate(
            ConversationListQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                channel=parse_channel(channel),
                status=parse_status(status),
                date_from=parse_local_date(date_from, "from"),
                date_to=parse_local_date(date_to, "to"),
                search=parse_search(search),
                include_sandbox=parse_include_sandbox(include_sandbox),
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
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

    @router.get("/v1/businesses/{business_id}/conversations/{conversation_id}/messages")
    def list_conversation_messages(
        request: Request,
        business_id: str,
        conversation_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> MessagePage:
        return list_conversation_messages_operator.operate(
            ConversationMessagesQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                conversation_id=parse_path_identifier(
                    conversation_id, ConversationId, "Conversation"
                ),
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.put(
        "/v1/businesses/{business_id}/conversations/{conversation_id}/rating",
        openapi_extra=describe_json_body(ConversationRatingRequest),
    )
    def rate_conversation(
        business_id: str,
        conversation_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ConversationRatingRequest, Depends(read_rating_body)],
    ) -> ConversationSummaryView:
        return rate_conversation_operator.operate(
            RateConversationCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                conversation_id=parse_path_identifier(
                    conversation_id,
                    ConversationId,
                    "Conversation",
                ),
                rating=body.rating,
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/conversations/{conversation_id}/messages",
        status_code=201,
        openapi_extra=describe_json_body(StaffMessageRequest),
    )
    def send_staff_message(
        request: Request,
        business_id: str,
        conversation_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[StaffMessageRequest, Depends(read_staff_message_body)],
    ) -> StaffMessageResult:
        return send_staff_message_operator.operate(
            SendStaffMessageCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                conversation_id=parse_path_identifier(
                    conversation_id,
                    ConversationId,
                    "Conversation",
                ),
                text=body.text,
                as_template=body.as_template,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(
        "/v1/businesses/{business_id}/calls/{call_id}/recording",
        response_class=Response,
        responses=RECORDING_OPENAPI_RESPONSES,
    )
    def get_call_recording(
        request: Request,
        business_id: str,
        call_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        requested_range: ByteRange | None = read_byte_range(
            request.headers.get("range"),
            request.headers.get("if-range"),
        )
        audio: RecordingAudio = get_call_recording_operator.operate(
            CallRecordingQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                call_id=parse_path_identifier(call_id, CallId, "Call"),
                client_ip_address=read_client_ip_address(request),
                starts_playback=(
                    requested_range is None or requested_range.starts_at_beginning()
                ),
            )
        )
        return build_recording_response(audio, requested_range)

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
