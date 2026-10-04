import logging

from app.contracts.llm import LlmAdapterContract
from app.contracts.reply_safety import ClaimCheckFacilitatorContract
from app.facilitators.claim_check.verifier_answers import read_verdicts
from app.facilitators.claim_check.verifier_prompt import (
    VERIFIER_INSTRUCTION,
    build_verifier_question,
)
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.reply_safety import ClaimVerdict
from app.schemas.domain.conversations import ClaimFinding
from app.schemas.dto.conversations import LlmCallLimits, LlmRequest, LlmResponse
from app.schemas.dto.reply_safety import (
    ClaimCheckRequest,
    ClaimCheckResult,
    VerifierUsage,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.assistants.constrained_integers import (
    LlmCallRetryLimit,
    LlmCallTimeoutSeconds,
    LlmMaxOutputTokens,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import MessageText

LOGGER: logging.Logger = logging.getLogger(__name__)
VERIFIER_MAX_OUTPUT_TOKENS: int = 400
# The customer waits for this check: a slow verifier is skipped, not retried.
VERIFIER_TIMEOUT_SECONDS: int = 12


class ClaimCheckFacilitator(ClaimCheckFacilitatorContract):
    """
    Asks a cheap verifier model (LLM_VERIFIER_MODEL_ID) whether the
    business's evidence backs each policy or availability claim of a
    reply ("parking is free", "we take dogs").

    One short call per reply that makes such claims, without tools and with
    the least reasoning effort, bounded by a timeout and never retried: the
    customer is waiting. A failed, refused or unreadable answer leaves the
    claims UNCHECKED and the reply goes out (the number guard still ran).
    Without a verifier model the check is off and finds nothing.
    """

    def __init__(
        self,
        llm_adapter: LlmAdapterContract,
        verifier_model_id: LlmModelId | None,
    ) -> None:
        self._llm_adapter: LlmAdapterContract = llm_adapter
        self._verifier_model_id: LlmModelId | None = verifier_model_id

    def check_claims(self, request: ClaimCheckRequest) -> ClaimCheckResult:
        if self._verifier_model_id is None or not request.claims:
            return ClaimCheckResult()

        model_id: LlmModelId = self._verifier_model_id
        try:
            response: LlmResponse = self._llm_adapter.complete(
                LlmRequest(
                    model_id=model_id,
                    system_prompt=SystemPromptText(VERIFIER_INSTRUCTION),
                    tools=[],
                    transcript=[
                        self._llm_adapter.build_user_text_turn(
                            MessageText(
                                build_verifier_question(
                                    request.claims, request.evidence
                                )
                            )
                        )
                    ],
                    max_output_tokens=LlmMaxOutputTokens(VERIFIER_MAX_OUTPUT_TOKENS),
                    effort=LlmEffort.MINIMAL,
                    call_limits=LlmCallLimits(
                        timeout_seconds=LlmCallTimeoutSeconds(VERIFIER_TIMEOUT_SECONDS),
                        retry_limit=LlmCallRetryLimit(0),
                    ),
                )
            )
        except ExternalServiceError, LlmRefusedError:
            LOGGER.warning("The claim verifier did not answer; claims unchecked.")
            return ClaimCheckResult(findings=unchecked_findings(request))

        verdicts: list[ClaimVerdict] = read_verdicts(
            None if response.text is None else str(response.text),
            len(request.claims),
        )
        return ClaimCheckResult(
            findings=[
                ClaimFinding(
                    claim=candidate.claim, topic=candidate.topic, verdict=verdict
                )
                for candidate, verdict in zip(request.claims, verdicts, strict=True)
            ],
            usage=VerifierUsage(
                model_id=model_id,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            ),
        )


def unchecked_findings(request: ClaimCheckRequest) -> list[ClaimFinding]:
    return [
        ClaimFinding(
            claim=candidate.claim,
            topic=candidate.topic,
            verdict=ClaimVerdict.UNCHECKED,
        )
        for candidate in request.claims
    ]
