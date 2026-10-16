"""The invented-numbers audit of a finished phone call (concept section 5)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.conversations import CallGuardVerdict
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine, RecordedCall
from app.schemas.typings.conversations.strings import UnverifiedReplyValue
from app.schemas.typings.handoffs.prefixed_id import HandoffId


class CallAuditRequest(ImmutableDTO):
    """A call just stored, with the transcript the voice platform reported."""

    call: RecordedCall
    transcript: list[FinishedCallTranscriptLine] = Field(
        default_factory=list[FinishedCallTranscriptLine]
    )


class CallAudit(ImmutableDTO):
    """
    What the audit found: no verdict for a call that was not newly stored
    (ignored or a repeated webhook), else the verdict, the values no
    evidence backs and the handoff opened for staff, if any.
    """

    guard_verdict: CallGuardVerdict | None = None
    unverified_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
    handoff_id: HandoffId | None = None
