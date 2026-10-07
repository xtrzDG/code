"""What happened during a call: its conversation, bookings, leads, handoffs."""

from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.voice_webhooks import FinishedCallReport
from app.schemas.typings.conversations.strings import ChannelUserId


def find_call_conversation(
    conversation_repo: ConversationRepoContract,
    business: BusinessDocument,
    report: FinishedCallReport,
) -> ConversationDocument | None:
    conversations: list[ConversationDocument] = conversation_repo.list_by_channel_user(
        business.id, ChannelKind.PHONE, ChannelUserId(str(report.provider_call_id))
    )
    return conversations[0] if conversations else None


def list_call_bookings(
    booking_repo: BookingRepoContract,
    business: BusinessDocument,
    conversation: ConversationDocument | None,
) -> list[BookingDocument]:
    if conversation is None:
        return []

    bookings: list[BookingDocument] = [
        booking
        for booking in booking_repo.list_by_business(business.id)
        if booking.conversation_id == conversation.id
        and booking.status is not BookingStatus.CANCELLED
    ]
    return sorted(bookings, key=lambda booking: booking.created_at)


def has_call_lead(
    lead_repo: LeadRepoContract,
    business: BusinessDocument,
    conversation: ConversationDocument | None,
) -> bool:
    return conversation is not None and any(
        lead.conversation_id == conversation.id
        for lead in lead_repo.list_by_business(business.id)
    )


def has_call_handoff(
    handoff_repo: HandoffRepoContract,
    business: BusinessDocument,
    conversation: ConversationDocument | None,
) -> bool:
    return conversation is not None and any(
        handoff.conversation_id == conversation.id
        for handoff in handoff_repo.list_by_business(business.id)
    )
