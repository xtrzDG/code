"""
What backs the values the phone assistant said during a call.

Trusted evidence is what the business and the server told the agent: the
business name, the fact table of the call's assistant version, the call's
own date context (the "Current call" lines it got when the call started),
the results of the tools it called (recorded with the call's conversation)
and the caller's bookings. What the caller said backs times, dates, phones
and counts, never a price, exactly as in chat.
"""

from collections.abc import Sequence

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.utilities.conversations.turn_context import (
    describe_local_now,
    describe_next_days,
)
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    to_local_moment,
)


def collect_call_evidence(
    message_repo: MessageRepoContract,
    booking_repo: BookingRepoContract,
    business: BusinessDocument,
    call: CallDocument,
    conversation: ConversationDocument | None,
    version: AssistantVersionDocument | None,
) -> list[str]:
    """Trusted texts that may back a value of the agent's lines."""

    zone = load_time_zone(business.timezone)
    call_start = to_local_moment(microseconds_to_seconds(int(call.started_at)), zone)
    evidence: list[str] = [
        str(business.name),
        f"Local time at the business: {describe_local_now(call_start)} "
        f"({business.timezone}).",
        f"Next days: {describe_next_days(call_start)}.",
    ]
    if version is not None:
        evidence.extend(f"{fact.label}: {fact.value}" for fact in version.facts)

    if conversation is None:
        return evidence

    for message in message_repo.list_by_conversation(business.id, conversation.id):
        evidence.extend(
            str(record.result_json)
            for record in message.tool_calls
            if not record.is_error
        )

    evidence.extend(
        f"Booking: {describe_local_now(to_local_moment(int(booking.starts_at), zone))}"
        f", {int(booking.party_size)} people"
        for booking in booking_repo.list_by_business(business.id)
        if booking.contact_id == conversation.contact_id
        and booking.status in BLOCKING_BOOKING_STATUSES
    )
    return evidence


def split_call_lines(
    transcript: Sequence[FinishedCallTranscriptLine],
) -> tuple[list[str], list[str]]:
    """(the agent's lines, the caller's lines) in the order they were said."""

    agent_lines: list[str] = [
        str(line.text)
        for line in transcript
        if line.author is MessageAuthor.ASSISTANT and str(line.text).strip()
    ]
    caller_lines: list[str] = [
        str(line.text) for line in transcript if line.author is MessageAuthor.CUSTOMER
    ]
    return agent_lines, caller_lines
