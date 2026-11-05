"""
How a reply the engine could not send becomes a handoff: the reason, the
code staff read in their language, and the values the guard flagged.

Unsupported claims are reported with the code of held-back values (its
text speaks of figures or statements the business details do not back)
and another person's contact details as a declined answer, without the
details themselves: codes of their own come only in a release after the
one that knows them (docs/operations/deploys.md, enum values).
"""

from app.schemas.constants.conversation_engine import ReplyFailureKind
from app.schemas.constants.handoffs import HandoffReason, HandoffSummaryCode
from app.schemas.constants.reply_safety import ClaimVerdict
from app.schemas.dto.conversation_engine import GeneratedReply, PreparedTurn
from app.schemas.dto.handoffs import CodedHandoffSummary
from app.schemas.typings.conversations.strings import UnverifiedReplyValue
from app.schemas.typings.handoffs.strings import HandoffQuotedText

MAX_QUOTED_CUSTOMER_TEXT: int = 300
MAX_FLAGGED_CLAIM_LENGTH: int = 120
FAILURE_HANDOFF_REASONS: dict[ReplyFailureKind, HandoffReason] = {
    ReplyFailureKind.REFUSAL: HandoffReason.SENSITIVE_TOPIC,
    ReplyFailureKind.PROVIDER_ERROR: HandoffReason.NON_STANDARD_REQUEST,
    ReplyFailureKind.NO_ANSWER: HandoffReason.NON_STANDARD_REQUEST,
    ReplyFailureKind.UNVERIFIED_NUMBERS: HandoffReason.UNVERIFIED_NUMBERS,
    ReplyFailureKind.UNSUPPORTED_CLAIM: HandoffReason.UNKNOWN_ANSWER,
    ReplyFailureKind.PERSONAL_DATA: HandoffReason.SENSITIVE_TOPIC,
}
FAILURE_SUMMARY_CODES: dict[ReplyFailureKind, HandoffSummaryCode] = {
    ReplyFailureKind.REFUSAL: HandoffSummaryCode.MODEL_DECLINED,
    ReplyFailureKind.PROVIDER_ERROR: HandoffSummaryCode.MODEL_UNAVAILABLE,
    ReplyFailureKind.NO_ANSWER: HandoffSummaryCode.ANSWER_UNFINISHED,
    ReplyFailureKind.UNVERIFIED_NUMBERS: HandoffSummaryCode.UNVERIFIED_VALUES,
    ReplyFailureKind.UNSUPPORTED_CLAIM: HandoffSummaryCode.UNVERIFIED_VALUES,
    ReplyFailureKind.PERSONAL_DATA: HandoffSummaryCode.MODEL_DECLINED,
}


def build_failure_summary(
    turn: PreparedTurn, generated: GeneratedReply
) -> CodedHandoffSummary:
    """
    Summary for staff: what went wrong (a code each reader's language
    renders), the values or claims the guard flagged and what the customer
    wrote.
    """

    failure: ReplyFailureKind = (
        ReplyFailureKind.NO_ANSWER if generated.failure is None else generated.failure
    )
    return CodedHandoffSummary(
        code=FAILURE_SUMMARY_CODES[failure],
        quoted_text=HandoffQuotedText(
            str(turn.customer_text)[:MAX_QUOTED_CUSTOMER_TEXT]
        ),
        flagged_values=flagged_values(failure, generated),
    )


def flagged_values(
    failure: ReplyFailureKind, generated: GeneratedReply
) -> list[UnverifiedReplyValue]:
    """Values for a values failure, claims for a claims one, else nothing."""

    if failure is ReplyFailureKind.UNSUPPORTED_CLAIM:
        return [
            UnverifiedReplyValue(str(finding.claim)[:MAX_FLAGGED_CLAIM_LENGTH])
            for finding in generated.claim_findings
            if finding.verdict is ClaimVerdict.UNSUPPORTED
        ]

    if failure is ReplyFailureKind.PERSONAL_DATA:
        return []

    return list(generated.unverified_values)
