"""
The reply guard's look at one reply text: invented values and links,
unsupported policy and availability claims, a booking said to be done that
no booking tool of the turn made, other people's contact details and
quoted team notes.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.contracts.registries import CountryRegistryContract
from app.contracts.reply_safety import ClaimCheckFacilitatorContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.conversation_engine import ReplyFailureKind
from app.schemas.constants.reply_safety import (
    ClaimTopic,
    ClaimVerdict,
    ReplyGuardReason,
)
from app.schemas.domain.conversations import ClaimFinding
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.reply_safety import (
    ClaimCandidate,
    ClaimCheckRequest,
    ClaimCheckResult,
    VerifierUsage,
)
from app.schemas.typings.conversations.strings import (
    ClaimText,
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
from app.utilities.reply_guard.booking_claims import find_unbacked_booking_claims
from app.utilities.reply_guard.claim_candidates import find_claim_candidates
from app.utilities.reply_guard.deposit_amount_check import (
    find_deposit_amount_mismatches,
)
from app.utilities.reply_guard.reply_links import find_foreign_links
from app.utilities.reply_guard.team_note_quotes import (
    find_quoted_notes,
    find_transcript_notes,
)


@dataclass(frozen=True)
class ReplyReview:
    """
    What the guard found in one reply text (technical record). A link the
    business did not publish is held back like an invented value, a quoted
    team note like another person's details (the stored reasons stay the
    ones the release before knows).
    """

    unverified_values: list[UnverifiedReplyValue] = field(
        default_factory=list[UnverifiedReplyValue]
    )
    claim_findings: list[ClaimFinding] = field(default_factory=list[ClaimFinding])
    withheld_details: list[str] = field(default_factory=list[str])
    verifier_usage: list[VerifierUsage] = field(default_factory=list[VerifierUsage])
    foreign_links: list[UnverifiedReplyValue] = field(
        default_factory=list[UnverifiedReplyValue]
    )
    quoted_notes: list[str] = field(default_factory=list[str])
    # Sentences saying a booking is done with no booking tool success in the
    # turn; also in `claim_findings` as unsupported (stored as claims).
    booking_claims: list[str] = field(default_factory=list[str])

    @property
    def flagged_values(self) -> list[UnverifiedReplyValue]:
        """The invented values and the foreign links, as stored and reported."""

        return [*self.unverified_values, *self.foreign_links]

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
        if self.withheld_details or self.quoted_notes:
            reasons.append(ReplyGuardReason.PERSONAL_DATA)

        if self.flagged_values:
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
    guard (and, in a turn that asked a deposit, the deposit's amount; the
    country's emergency number is the platform's own), the links (the
    business's, the platform's and well-known map and payment links), the
    personal data check, the team notes the model was shown and, when a
    sentence states a policy or an availability, the claim check's
    verifier model.
    """

    def __init__(
        self,
        message_repo: MessageRepoContract,
        contact_repo: ContactRepoContract,
        claim_check: ClaimCheckFacilitatorContract,
        country_registry: CountryRegistryContract | None = None,
        platform_hosts: Sequence[str] = (),
    ) -> None:
        self._message_repo: MessageRepoContract = message_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._claim_check: ClaimCheckFacilitatorContract = claim_check
        self._country_registry: CountryRegistryContract | None = country_registry
        self._platform_hosts: tuple[str, ...] = tuple(platform_hosts)

    def review(
        self, turn: PreparedTurn, progress: TurnProgress, reply_text: MessageText
    ) -> ReplyReview:
        """
        The reply as the customer will read it: with the prompt and the
        options it offers (an invented time on a button is held back too).
        """

        text = MessageText(text_with_options(str(reply_text), progress.choices))
        evidence: ReplyEvidence = gather_reply_evidence(
            self._message_repo, turn, progress, self._platform_texts(turn)
        )
        candidates: list[ClaimCandidate] = find_claim_candidates(
            str(text), [*turn.version.languages, turn.reply_language]
        )
        booking_claims: list[str] = find_unbacked_booking_claims(
            str(text),
            [*turn.version.languages, turn.reply_language],
            progress.tool_calls,
            evidence.tool_calls,
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
            unverified_values=unique_values(
                [
                    *find_unverified_reply_values(evidence, turn, text),
                    *find_deposit_amount_mismatches(
                        text,
                        [line.amount for line in progress.deposit_lines],
                        [*turn.version.languages, turn.reply_language],
                    ),
                ]
            ),
            claim_findings=[
                *result.findings,
                *(unbacked_booking_finding(claim) for claim in booking_claims),
            ],
            booking_claims=booking_claims,
            withheld_details=find_withheld_contact_details(
                self._contact_repo, turn, str(text), evidence
            ),
            verifier_usage=[] if result.usage is None else [result.usage],
            foreign_links=[
                UnverifiedReplyValue(link)
                for link in find_foreign_links(
                    str(text), evidence.trusted, self._platform_hosts
                )
            ],
            quoted_notes=find_quoted_notes(
                str(text), find_transcript_notes(progress.transcript)
            ),
        )

    def _platform_texts(self, turn: PreparedTurn) -> list[str]:
        """The platform's own lines a reply may repeat: the emergency number."""

        if self._country_registry is None:
            return []

        number: str = str(
            self._country_registry.get(turn.business.country_code).emergency_number
        )
        return [f"Emergency number: {number}"]


def unbacked_booking_finding(claim: str) -> ClaimFinding:
    """
    A booking claim as the stored claim findings keep it: an unsupported
    statement of availability (the reasons and topics the release before
    reads).
    """

    return ClaimFinding(
        claim=ClaimText(claim),
        topic=ClaimTopic.AVAILABILITY,
        verdict=ClaimVerdict.UNSUPPORTED,
    )


def unique_values(
    values: list[UnverifiedReplyValue],
) -> list[UnverifiedReplyValue]:
    """The values in order, each once."""

    return list(dict.fromkeys(values))
