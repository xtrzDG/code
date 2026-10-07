"""
The reply guard's look at one reply text: invented values, unsupported
policy and availability claims, and other people's contact details.
"""

from dataclasses import dataclass, field

from app.contracts.reply_safety import ClaimCheckFacilitatorContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.conversation_engine import ReplyFailureKind
from app.schemas.constants.reply_safety import ClaimVerdict, ReplyGuardReason
from app.schemas.domain.conversations import ClaimFinding
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.reply_safety import (
    ClaimCandidate,
    ClaimCheckRequest,
    ClaimCheckResult,
    VerifierUsage,
)
from app.schemas.typings.conversations.strings import (
    MessageText,
    ReplyEvidenceText,
    UnverifiedReplyValue,
)
from app.use_cases.conversations.replies.personal_data_check import (
    find_withheld_contact_details,
)
from app.use_cases.conversations.replies.reply_evidence import (
    ReplyEvidence,
    find_unverified_reply_values,
    gather_reply_evidence,
)
from app.use_cases.conversations.replies.turn_progress import TurnProgress
from app.utilities.conversations.reply_choices_text import text_with_options
from app.utilities.reply_guard.claim_candidates import find_claim_candidates


@dataclass(frozen=True)
class ReplyReview:
    """What the guard found in one reply text (technical record)."""

    unverified_values: list[UnverifiedReplyValue] = field(
        default_factory=list[UnverifiedReplyValue]
    )
    claim_findings: list[ClaimFinding] = field(default_factory=list[ClaimFinding])
    withheld_details: list[str] = field(default_factory=list[str])
    verifier_usage: list[VerifierUsage] = field(default_factory=list[VerifierUsage])

    @property
    def unsupported_claims(self) -> list[ClaimFinding]:
        return [
            finding
            for finding in self.claim_findings
            if finding.verdict is ClaimVerdict.UNSUPPORTED
        ]

    @property
    def reasons(self) -> list[ReplyGuardReason]:
        """Why the reply may not be sent as it is, most serious first."""

        reasons: list[ReplyGuardReason] = []
        if self.withheld_details:
            reasons.append(ReplyGuardReason.PERSONAL_DATA)

        if self.unverified_values:
            reasons.append(ReplyGuardReason.UNVERIFIED_VALUES)

        if self.unsupported_claims:
            reasons.append(ReplyGuardReason.UNSUPPORTED_CLAIMS)

        return reasons

    @property
    def failure(self) -> ReplyFailureKind:
        """The failure a reply still held back after its rewrite reports."""

        reasons: list[ReplyGuardReason] = self.reasons
        if ReplyGuardReason.PERSONAL_DATA in reasons:
            return ReplyFailureKind.PERSONAL_DATA

        if ReplyGuardReason.UNVERIFIED_VALUES in reasons:
            return ReplyFailureKind.UNVERIFIED_NUMBERS

        return ReplyFailureKind.UNSUPPORTED_CLAIM


class ReplyReviewer:
    """
    Reviews a reply text against the conversation's evidence: the numbers
    guard, the personal data check and, when a sentence states a policy or
    an availability, the claim check's verifier model.
    """

    def __init__(
        self,
        message_repo: MessageRepoContract,
        contact_repo: ContactRepoContract,
        claim_check: ClaimCheckFacilitatorContract,
    ) -> None:
        self._message_repo: MessageRepoContract = message_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._claim_check: ClaimCheckFacilitatorContract = claim_check

    def review(
        self, turn: PreparedTurn, progress: TurnProgress, reply_text: MessageText
    ) -> ReplyReview:
        """
        The reply as the customer will read it: with the prompt and the
        options it offers (an invented time on a button is held back too).
        """

        text = MessageText(text_with_options(str(reply_text), progress.choices))
        evidence: ReplyEvidence = gather_reply_evidence(
            self._message_repo, turn, progress
        )
        candidates: list[ClaimCandidate] = find_claim_candidates(
            str(text), [*turn.version.languages, turn.reply_language]
        )
        result: ClaimCheckResult = (
            self._claim_check.check_claims(
                ClaimCheckRequest(
                    claims=candidates,
                    evidence=[ReplyEvidenceText(item) for item in evidence.trusted],
                    language=turn.reply_language,
                )
            )
            if candidates
            else ClaimCheckResult()
        )
        return ReplyReview(
            unverified_values=find_unverified_reply_values(evidence, turn, text),
            claim_findings=list(result.findings),
            withheld_details=find_withheld_contact_details(
                self._contact_repo, turn, str(text), evidence
            ),
            verifier_usage=[] if result.usage is None else [result.usage],
        )
