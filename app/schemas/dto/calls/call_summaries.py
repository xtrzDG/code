"""
Summaries of phone calls for staff: what a call left behind, the request
to summarize it, and one staff text about it in one language.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.calls import (
    MissedCallReason,
    TextBackChannel,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.constants.conversations import CallOutcome
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine, RecordedCall
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.calls.booleans import IsCallSummaryGenerated
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
)
from app.schemas.typings.conversations.strings import UnverifiedReplyValue
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import FormattedPhoneNumber


class TextBackNote(ImmutableDTO):
    """What became of the message to a caller who did not get through."""

    status: TextBackStatus
    channel: TextBackChannel | None = None
    skip_reason: TextBackSkipReason | None = None


class CallSummaryRequest(ImmutableDTO):
    """
    A call just stored, with the transcript the voice platform reported and,
    when its caller did not get through, the missed call (with the
    text-back they get).
    """

    call: RecordedCall
    transcript: list[FinishedCallTranscriptLine] = Field(
        default_factory=list[FinishedCallTranscriptLine]
    )
    missed_call: MissedCallDocument | None = None


class CallSummaryOutcome(ImmutableDTO):
    """Whether a summary was written now and how many staff alerts were queued."""

    is_generated: IsCallSummaryGenerated = False
    notified_count: DeliveredNotificationCount = DeliveredNotificationCount(0)


class CallBookingNote(ImmutableDTO):
    """The booking a call made: when it starts and for how many."""

    starts_at: BookingStartsAtUnixSeconds
    party_size: PartySize


class CallReportTextInput(ImmutableDTO):
    """
    One staff text about a call, in one language: who called and when, the
    summary, how it ended (a booking with its time), the values the phone
    assistant said that the business data does not back, and, for a caller
    who did not get through, why and what they were sent.
    """

    business_name: BusinessName
    language: LanguageTag
    timezone: TimezoneName
    started_at: Microseconds
    caller_phone: FormattedPhoneNumber | None = None
    caller_name: ContactName | None = None
    duration_seconds: CallDurationSeconds | None = None
    outcome: CallOutcome | None = None
    summary: CallSummaryText | None = None
    booking: CallBookingNote | None = None
    unverified_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
    missed_reason: MissedCallReason | None = None
    text_back: TextBackNote | None = None
