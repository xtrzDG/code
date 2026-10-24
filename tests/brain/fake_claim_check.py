"""A claim check that answers from a table instead of a verifier model."""

from collections.abc import Mapping

from app.contracts.reply_safety import ClaimCheckFacilitatorContract
from app.schemas.constants.reply_safety import ClaimVerdict
from app.schemas.domain.conversations import ClaimFinding
from app.schemas.dto.reply_safety import (
    ClaimCheckRequest,
    ClaimCheckResult,
    VerifierUsage,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount

FAKE_VERIFIER_MODEL: LlmModelId = LlmModelId("gpt-5-nano")


class FakeClaimCheck(ClaimCheckFacilitatorContract):
    """
    Judges each claim by the first verdict whose key it contains (case
    insensitive), SUPPORTED otherwise; records every request. Off (finds
    nothing, records nothing) when built with `is_enabled=False`.
    """

    def __init__(
        self,
        verdicts: Mapping[str, ClaimVerdict] | None = None,
        is_enabled: bool = True,
    ) -> None:
        self._verdicts: dict[str, ClaimVerdict] = dict(verdicts or {})
        self._is_enabled: bool = is_enabled
        self.requests: list[ClaimCheckRequest] = []

    def check_claims(self, request: ClaimCheckRequest) -> ClaimCheckResult:
        if not self._is_enabled:
            return ClaimCheckResult()

        self.requests.append(request)
        return ClaimCheckResult(
            findings=[
                ClaimFinding(
                    claim=candidate.claim,
                    topic=candidate.topic,
                    verdict=self._judge(str(candidate.claim)),
                )
                for candidate in request.claims
            ],
            usage=VerifierUsage(
                model_id=FAKE_VERIFIER_MODEL,
                input_tokens=LlmTokenCount(1000),
                output_tokens=LlmTokenCount(20),
            ),
        )

    def _judge(self, claim: str) -> ClaimVerdict:
        for key, verdict in self._verdicts.items():
            if key.lower() in claim.lower():
                return verdict

        return ClaimVerdict.SUPPORTED
