"""What the reply guard did with a message, as the cabinet shows it."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.constants.reply_safety import (
    ClaimTopic,
    ClaimVerdict,
    InjectionSignal,
    ReplyGuardReason,
)
from app.schemas.typings.conversations.strings import (
    ClaimText,
    UnverifiedReplyValue,
)


class ClaimFindingView(ImmutableDTO):
    """One policy or availability claim of a reply and the verifier's verdict."""

    claim: ClaimText
    topic: ClaimTopic
    verdict: ClaimVerdict


class MessageGuardView(ImmutableDTO):
    """
    The reply guard's record of a message: for the assistant's reply its
    verdict (clean, rewritten once, handed to staff), why it held the reply
    back, the values the evidence did not back and the claims it checked;
    for a customer message the kind of prompt injection it looked like.
    """

    verdict: ReplyGuardVerdict | None = None
    reasons: list[ReplyGuardReason] = Field(default_factory=list[ReplyGuardReason])
    unverified_values: list[UnverifiedReplyValue] = Field(
        default_factory=list[UnverifiedReplyValue]
    )
    claim_findings: list[ClaimFindingView] = Field(
        default_factory=list[ClaimFindingView]
    )
    injection_flag: InjectionSignal | None = None
