"""Documents of the platform's operations tests, built with the fields that matter."""

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind, ChannelStatus, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import MessageDocument, ToolCallRecord
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.jobs import QueuedJobDocument, WorkerHeartbeatDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import ChannelErrorSummary
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.platform.constrained_strings import (
    JobName,
    ReleaseVersion,
    WorkerHostName,
)
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.deliveries.delivery_keys import derive_outbound_message_id

# Monday 2026-10-05 08:00 UTC.
NOW: Microseconds = Microseconds(1_791_187_200_000_000)
SECOND: int = 1_000_000
MINUTE: int = 60 * SECOND
HOUR: int = 60 * MINUTE
DAY: int = 24 * HOUR
RELEASE: ReleaseVersion = ReleaseVersion("4718714c0f2e")


def at(offset: int) -> Microseconds:
    """A moment `offset` microseconds after NOW (negative: before)."""

    return Microseconds(int(NOW) + offset)


def job(
    status: QueuedJobStatus,
    lane: JobLane = JobLane.DEFAULT,
    run_at: Microseconds = NOW,
    name: str = "send_owner_digest",
) -> QueuedJobDocument:
    return QueuedJobDocument(
        name=JobName(name),
        payload=JobPayloadJson("{}"),
        lane=lane,
        run_at=run_at,
        status=status,
        created_at=run_at,
        updated_at=run_at,
    )


def pulse(
    host: str,
    beat_at: Microseconds,
    started_at: Microseconds | None = None,
    release: ReleaseVersion | None = RELEASE,
) -> WorkerHeartbeatDocument:
    started: Microseconds = at(-DAY) if started_at is None else started_at
    return WorkerHeartbeatDocument(
        host_name=WorkerHostName(host),
        release=release,
        started_at=started,
        beat_at=beat_at,
        created_at=started,
        updated_at=beat_at,
    )


def channel(
    business_id: BusinessId,
    status: ChannelStatus = ChannelStatus.CONNECTED,
    kind: ChannelKind = ChannelKind.WHATSAPP,
    expires_at: Microseconds | None = None,
) -> ChannelDocument:
    return ChannelDocument(
        business_id=business_id,
        kind=kind,
        status=status,
        last_error=(
            ChannelErrorSummary("Meta rejected the access token (190).")
            if status is ChannelStatus.ERROR
            else None
        ),
        last_error_at=at(-HOUR) if status is ChannelStatus.ERROR else None,
        credential_expires_at=expires_at,
        created_at=at(-30 * DAY),
        updated_at=at(-HOUR),
    )


def handoff(
    business_id: BusinessId,
    created_at: Microseconds,
    is_sandbox: bool = False,
) -> HandoffDocument:
    return HandoffDocument(
        business_id=business_id,
        conversation_id=ConversationId(),
        contact_id=ContactId(),
        reason=HandoffReason.CUSTOMER_REQUEST,
        summary=HandoffSummary("The customer asks for a person."),
        is_sandbox=is_sandbox,
        created_at=created_at,
        updated_at=created_at,
    )


def outbound(
    business_id: BusinessId,
    status: OutboundMessageStatus,
    created_at: Microseconds,
) -> OutboundMessageDocument:
    key = OutboundIdempotencyKey(f"reply:{int(created_at)}:{status.value}")
    return OutboundMessageDocument(
        id=derive_outbound_message_id(business_id, key),
        business_id=business_id,
        kind=OutboundMessageKind.CUSTOMER_REPLY,
        idempotency_key=key,
        recipient_key=OutboundRecipientKey("customer:channel_1:9001"),
        text=MessageText("Your table is booked."),
        status=status,
        created_at=created_at,
        updated_at=created_at,
    )


def reply(
    business_id: BusinessId,
    created_at: Microseconds,
    has_failed_tool: bool,
) -> MessageDocument:
    return MessageDocument(
        conversation_id=ConversationId(),
        business_id=business_id,
        direction=MessageDirection.OUTBOUND,
        author=MessageAuthor.ASSISTANT,
        text=MessageText("Let me check that for you."),
        tool_calls=[
            ToolCallRecord(
                tool_name=AssistantToolName.CHECK_AVAILABILITY,
                input_json=LlmToolInputJson("{}"),
                result_json=LlmToolResultJson('{"error": "calendar down"}'),
                is_error=has_failed_tool,
            )
        ],
        created_at=created_at,
        updated_at=created_at,
    )


def business(name: str, *members: BusinessMember) -> BusinessDocument:
    """A Georgian restaurant with the given members (owners, staff)."""

    return BusinessDocument(
        name=BusinessName(name),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode("GE"),
        timezone=TimezoneName("Asia/Tbilisi"),
        currency_code=CurrencyCode("GEL"),
        languages=[LanguageTag("ka"), LanguageTag("en")],
        default_language=LanguageTag("ka"),
        owner_language=LanguageTag("ka"),
        plan_key=PlanKey.VOICE_AND_CHAT,
        data_region=DataRegion.EU,
        members=list(members),
        created_at=at(-30 * DAY),
        updated_at=at(-30 * DAY),
    )


def member(user_id: UserId, role: BusinessMemberRole) -> BusinessMember:
    return BusinessMember(user_id=user_id, role=role)
