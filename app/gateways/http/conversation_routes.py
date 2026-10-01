"""Conversation feed and the owner's test chat (cabinet, concept section 8)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.dto.call_recordings import CallRecordingQuery, RecordingAudio
from app.schemas.dto.conversation_feed import (
    ConversationDetailView,
    ConversationListQuery,
    ConversationPage,
    ConversationQuery,
    ConversationRatingRequest,
    ConversationSummaryView,
    OwnerTestChatCommand,
    OwnerTestChatRequest,
    RateConversationCommand,
    SendStaffMessageCommand,
    StaffMessageRequest,
    StaffMessageResult,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IncludeSandboxConversations
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSearchText,
)
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.users.prefixed_id import UserId

read_test_chat_body = build_json_body_dependency(OwnerTestChatRequest)
read_rating_body = build_json_body_dependency(ConversationRatingRequest)
read_staff_message_body = build_json_body_dependency(StaffMessageRequest)
# A recording is personal data: no HTTP cache keeps it (shared proxies and
# CDNs least of all); the browser's player buffers it in memory.
RECORDING_RESPONSE_HEADERS: dict[str, str] = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
}
RECORDING_OPENAPI_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "The call recording (audio/mpeg from the voice platform).",
        "content": {"audio/*": {"schema": {"type": "string", "format": "binary"}}},
    }
}
TRUE_FLAGS: frozenset[str] = frozenset({"1", "true", "yes"})
FALSE_FLAGS: frozenset[str] = frozenset({"0", "false", "no"})


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

    router = APIRouter(tags=["conversations"])

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
        audio: RecordingAudio = get_call_recording_operator.operate(
            CallRecordingQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                call_id=parse_path_identifier(call_id, CallId, "Call"),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(
            content=audio.content,
            media_type=str(audio.media_type),
            headers=RECORDING_RESPONSE_HEADERS,
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


def parse_status(raw_status: str | None) -> ConversationStatus | None:
    if raw_status is None or raw_status.strip() == "":
        return None

    try:
        return ConversationStatus(raw_status.strip().lower())
    except ValueError as error:
        known_statuses: str = ", ".join(status.value for status in ConversationStatus)
        raise ValidationFailedError(
            f"status must be one of: {known_statuses}."
        ) from error


def parse_local_date(raw_date: str | None, name: str) -> LocalDate | None:
    if raw_date is None or raw_date.strip() == "":
        return None

    try:
        return LocalDate(raw_date.strip())
    except (ValueError, TypeError) as error:
        raise ValidationFailedError(
            f"{name} must be a date like 2026-10-01."
        ) from error


def parse_search(raw_search: str | None) -> ConversationSearchText | None:
    if raw_search is None or raw_search.strip() == "":
        return None

    try:
        return ConversationSearchText(raw_search.strip())
    except (ValueError, TypeError) as error:
        raise ValidationFailedError(
            f"search may be at most {ConversationSearchText.max_length} characters."
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
