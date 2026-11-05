"""
What the voice platform's own evaluation of a call adds to the audit of
what the phone assistant said (`CallAnalysis`).
"""

import logging

from app.schemas.constants.calls import CallEvaluationResult
from app.schemas.constants.conversations import CallOutcome
from app.schemas.domain.call_analysis import CallAnalysis
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.conversations.strings import UnverifiedReplyValue

LOGGER: logging.Logger = logging.getLogger(__name__)
# How a finding of the evaluation is listed for staff.
PARTY_SIZE_NOTE: str = "people"
BOOKING_MISMATCH_NOTE: str = "booking does not match the request"


def booking_to_check(
    recorded: RecordedCall,
    analysis: CallAnalysis | None,
    values: list[UnverifiedReplyValue],
) -> list[UnverifiedReplyValue]:
    """
    What staff check when the voice platform found that a booking made in
    the call does not match the caller's request: the date, time and party
    size it read from the call (or a note when it read none), not listed
    twice.
    """

    if (
        analysis is None
        or recorded.outcome is not CallOutcome.BOOKING
        or analysis.booking_correct is not CallEvaluationResult.FAILURE
    ):
        return []

    asked: list[UnverifiedReplyValue] = [
        UnverifiedReplyValue(text)
        for text in (
            None if analysis.booking_date is None else str(analysis.booking_date),
            None if analysis.booking_time is None else str(analysis.booking_time),
            None
            if analysis.party_size is None
            else f"{int(analysis.party_size)} {PARTY_SIZE_NOTE}",
        )
        if text is not None
    ]
    return [
        value
        for value in asked or [UnverifiedReplyValue(BOOKING_MISMATCH_NOTE)]
        if value not in values
    ]


def warn_of_missing_disclosure(
    recorded: RecordedCall, analysis: CallAnalysis | None
) -> None:
    if (
        analysis is not None
        and analysis.disclosure_said is CallEvaluationResult.FAILURE
    ):
        LOGGER.warning(
            "Call %s of business %s: the voice platform heard no AI disclosure.",
            recorded.call_id,
            recorded.business_id,
        )
