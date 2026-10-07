"""
What a customer's erasure and the retention purge leave of the business
records: the record stays for the business's counts and statistics, what
is personal goes. Each function returns the record to store, or None when
there is nothing left to remove (so a repeated purge writes nothing).
"""

from typed_time_provider import Microseconds

from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber

ERASED_TEXT: str = "[erased at the visitor's request]"
EXPIRED_TEXT: str = "[removed after the retention period]"


def anonymized_lead(
    lead: LeadDocument, placeholder: str, now: Microseconds
) -> LeadDocument | None:
    """The lead without its details and budget."""

    if str(lead.details) in (ERASED_TEXT, EXPIRED_TEXT) and lead.budget is None:
        return None

    lead.details = LeadDetails(placeholder)
    lead.budget = None
    lead.updated_at = now
    return lead


def anonymized_booking(
    booking: BookingDocument, now: Microseconds
) -> BookingDocument | None:
    """The booking without the customer's notes."""

    if booking.notes is None:
        return None

    booking.notes = None
    booking.updated_at = now
    return booking


def anonymized_handoff(
    handoff: HandoffDocument,
    placeholder: str,
    summary_code: HandoffSummaryCode | None,
    now: Microseconds,
) -> HandoffDocument | None:
    """
    The handoff without its summary, quoted words and flagged values; the
    cabinet shows `summary_code` in the reader's language when there is one.
    """

    is_anonymized: bool = (
        str(handoff.summary) in (ERASED_TEXT, EXPIRED_TEXT)
        and handoff.quoted_text is None
        and not handoff.flagged_values
    )
    if is_anonymized:
        return None

    handoff.summary = HandoffSummary(placeholder)
    handoff.summary_code = summary_code
    handoff.quoted_text = None
    handoff.flagged_values = []
    handoff.updated_at = now
    return handoff


def erased_call(
    call: CallDocument,
    now: Microseconds,
    customer_phone: E164PhoneNumber | None = None,
) -> CallDocument | None:
    """
    The call without its recording, transcript, summaries for staff, the
    caller's number and the values its audit flagged. The number called
    goes when it is the customer's (`customer_phone`), or whenever no
    customer is named (the purge keeps no numbers at all). The recording
    file is deleted by the caller first.
    """

    is_called_number_personal: bool = call.to_phone_number is not None and (
        customer_phone is None or call.to_phone_number == customer_phone
    )
    has_content: bool = (
        call.recording_path is not None
        or call.transcript is not None
        or call.from_phone_number is not None
        or bool(call.summaries)
        or bool(call.unverified_values)
        or is_called_number_personal
    )
    if not has_content:
        return None

    call.recording_path = None
    call.transcript = None
    call.summaries = []
    call.unverified_values = []
    call.from_phone_number = None
    if is_called_number_personal:
        call.to_phone_number = None

    call.updated_at = now
    return call
