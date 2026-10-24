"""What the reply guard checks beyond numbers, and what it found."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.reply_safety import ClaimTopic
from app.schemas.domain.conversations import ClaimFinding
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.client_health.constrained_integers import (
    GuardedReplyCount,
    InjectionFlagCount,
)
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import (
    ClaimText,
    ReplyEvidenceText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class ClaimCandidate(ImmutableDTO):
    """A sentence of a reply that states a policy or an availability."""

    claim: ClaimText
    topic: ClaimTopic


class ClaimCheckRequest(ImmutableDTO):
    """
    The claims of one reply and everything that may back them: the facts,
    tool results, the server's context line and what staff wrote.
    """

    claims: list[ClaimCandidate]
    evidence: list[ReplyEvidenceText] = Field(default_factory=list[ReplyEvidenceText])
    language: LanguageTag


class VerifierUsage(ImmutableDTO):
    """The tokens one verifier call used, priced by its own model."""

    model_id: LlmModelId
    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)


class ClaimCheckResult(ImmutableDTO):
    """
    A finding per checked claim, in the request's order (empty when the
    claim check is off), and the verifier's usage when it was asked.
    """

    findings: list[ClaimFinding] = Field(default_factory=list[ClaimFinding])
    usage: VerifierUsage | None = None


class ClientGuardActivity(ImmutableDTO):
    """
    What the reply guard did for one client in a time window: the model's
    replies it checked, those it had rewritten once or handed to staff, and
    the customer messages that looked like prompt injection.
    """

    checked_replies: GuardedReplyCount = GuardedReplyCount(0)
    rewritten_replies: GuardedReplyCount = GuardedReplyCount(0)
    handed_off_replies: GuardedReplyCount = GuardedReplyCount(0)
    injection_flags: InjectionFlagCount = InjectionFlagCount(0)
