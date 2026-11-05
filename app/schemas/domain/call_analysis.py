"""The voice platform's own evaluation of a call (`CallDocument.analysis`)."""

from base_pydantic_schemas import PersistentDocument

from app.schemas.constants.calls import CallEvaluationResult
from app.schemas.typings.calls.booleans import IsCallbackRequested
from app.schemas.typings.calls.constrained_integers import CallCollectedPartySize
from app.schemas.typings.calls.constrained_strings import (
    CallCollectedDate,
    CallCollectedTime,
)


class CallAnalysis(PersistentDocument):
    """
    What the voice platform's evaluation of a finished call found, as the
    agent asks it to (R16-VOICE-TUNING): whether a booking matches what the
    caller asked (`booking_correct`) and whether the AI disclosure was said
    (`disclosure_said`), and what it read from the conversation: the date,
    time and party size of a booking asked for, and a request to be called
    back. Every field is None when the platform did not report it. No
    rationale text is kept: it would repeat what the caller said.
    """

    booking_correct: CallEvaluationResult | None = None
    disclosure_said: CallEvaluationResult | None = None
    booking_date: CallCollectedDate | None = None
    booking_time: CallCollectedTime | None = None
    party_size: CallCollectedPartySize | None = None
    callback_requested: IsCallbackRequested | None = None
