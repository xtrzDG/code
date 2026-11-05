"""The facts of a call's report to staff: who called, how it ended, what it made."""

from dataclasses import dataclass

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.calls.call_summaries import (
    CallBookingNote,
    CallReportTextInput,
    CallSummaryRequest,
    TextBackNote,
)
from app.schemas.dto.voice_webhooks import RecordedCall
from app.use_cases.shared.operations_support import display_phone


@dataclass(frozen=True)
class CallReportSources:
    """Where the report reads the caller and the booking the call made."""

    contact_repo: ContactRepoContract
    booking_repo: BookingRepoContract
    phone_number_parser: PhoneNumberParserContract


def build_call_report_facts(
    business: BusinessDocument,
    call: CallDocument,
    input_data: CallSummaryRequest,
    sources: CallReportSources,
) -> CallReportTextInput:
    """
    The call's facts in the owner's language: the caller's number and
    name, the duration, the outcome with the call's last booking, the
    values the assistant said that the business data does not back, and,
    for a caller who did not get through, why and whether they were
    written to.
    """

    recorded: RecordedCall = input_data.call
    missed: MissedCallDocument | None = input_data.missed_call
    contact: ContactDocument | None = (
        None
        if recorded.contact_id is None
        else sources.contact_repo.get(business.id, recorded.contact_id)
    )
    booking: BookingDocument | None = (
        None
        if not recorded.booking_ids
        else sources.booking_repo.get(business.id, recorded.booking_ids[-1])
    )
    return CallReportTextInput(
        business_name=business.name,
        language=business.owner_language,
        timezone=business.timezone,
        started_at=call.started_at,
        caller_phone=display_phone(sources.phone_number_parser, call.from_phone_number),
        caller_name=None if contact is None else contact.name,
        duration_seconds=call.duration_seconds,
        outcome=call.outcome,
        booking=(
            None
            if booking is None
            else CallBookingNote(
                starts_at=booking.starts_at, party_size=booking.party_size
            )
        ),
        unverified_values=list(call.unverified_values),
        missed_reason=None if missed is None else missed.reason,
        text_back=(
            None
            if missed is None
            else TextBackNote(
                status=missed.status,
                channel=missed.channel,
                skip_reason=missed.skip_reason,
            )
        ),
    )
