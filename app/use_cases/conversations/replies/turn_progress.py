"""What one reply turn produced so far, and the reply it becomes."""

from dataclasses import dataclass, field

from app.schemas.constants.conversation_engine import ReplyFailureKind
from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.constants.reply_safety import ReplyGuardReason
from app.schemas.domain.conversations import (
    ClaimFinding,
    LlmTurnDocument,
    ToolCallRecord,
)
from app.schemas.dto.assistant_tools import AssistantToolOutcome
from app.schemas.dto.conversation_engine import GeneratedReply, PreparedTurn
from app.schemas.dto.conversations import LlmResponse, LlmToolCall
from app.schemas.dto.reply_safety import VerifierUsage
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.conversations.constrained_integers import (
    LlmRoundCount,
    LlmTokenCount,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId


@dataclass
class TurnProgress:
    """
    What one turn produced so far (mutable technical state of the loop).

    `transcript` is replayed verbatim to the version's model;
    `canonical_transcript` is the same turns in the provider-neutral form,
    sent to a fallback model of another provider. `fallback_model_id` is
    the fallback that answered the latest round, if one did.
    """

    transcript: list[LlmProviderPayload]
    canonical_transcript: list[LlmProviderPayload]
    next_sequence_number: int
    tool_calls: list[ToolCallRecord] = field(default_factory=list[ToolCallRecord])
    tool_results: list[str] = field(default_factory=list[str])
    created_booking_ids: list[BookingId] = field(default_factory=list[BookingId])
    created_lead_ids: list[LeadId] = field(default_factory=list[LeadId])
    created_handoff_ids: list[HandoffId] = field(default_factory=list[HandoffId])
    input_tokens: int = 0
    output_tokens: int = 0
    rounds_used: int = 0
    fallback_model_id: LlmModelId | None = None
    is_fallback_model: bool = False


def start_progress(stored_turns: list[LlmTurnDocument]) -> TurnProgress:
    """The progress of a turn that continues the stored transcript."""

    return TurnProgress(
        transcript=[turn.payload for turn in stored_turns],
        canonical_transcript=[
            turn.payload if turn.canonical_payload is None else turn.canonical_payload
            for turn in stored_turns
        ],
        next_sequence_number=(
            0 if not stored_turns else int(stored_turns[-1].sequence_number) + 1
        ),
    )


def record_response(progress: TurnProgress, response: LlmResponse) -> None:
    """One more model call: its tokens, and which model answered it."""

    progress.rounds_used += 1
    progress.input_tokens += int(response.input_tokens)
    progress.output_tokens += int(response.output_tokens)
    progress.fallback_model_id = response.fallback_model_id
    if response.fallback_model_id is not None:
        progress.is_fallback_model = True


def record_tool_outcome(
    progress: TurnProgress,
    call: LlmToolCall,
    outcome: AssistantToolOutcome,
) -> None:
    """The call, its result (evidence when it succeeded) and what it created."""

    progress.tool_calls.append(
        ToolCallRecord(
            tool_name=outcome.tool_name,
            input_json=call.input_json,
            result_json=outcome.result.result_json,
            is_error=outcome.result.is_error,
        )
    )
    if not outcome.result.is_error:
        progress.tool_results.append(str(outcome.result.result_json))

    if outcome.booking_id is not None:
        progress.created_booking_ids.append(outcome.booking_id)

    if outcome.lead_id is not None:
        progress.created_lead_ids.append(outcome.lead_id)

    if outcome.handoff_id is not None:
        progress.created_handoff_ids.append(outcome.handoff_id)


def build_reply(
    turn: PreparedTurn,
    progress: TurnProgress,
    *,
    text: MessageText | None = None,
    failure: ReplyFailureKind | None = None,
    guard_verdict: ReplyGuardVerdict = ReplyGuardVerdict.CLEAN,
    unverified_values: list[UnverifiedReplyValue] | None = None,
    guard_reasons: list[ReplyGuardReason] | None = None,
    claim_findings: list[ClaimFinding] | None = None,
    verifier_usage: list[VerifierUsage] | None = None,
) -> GeneratedReply:
    """
    The turn's reply; its model is the one that answered the last round
    (the version's, or the fallback that stood in for it).
    """

    return GeneratedReply(
        text=text,
        failure=failure,
        guard_verdict=guard_verdict,
        guard_reasons=[] if guard_reasons is None else guard_reasons,
        unverified_values=[] if unverified_values is None else unverified_values,
        claim_findings=[] if claim_findings is None else claim_findings,
        verifier_usage=[] if verifier_usage is None else verifier_usage,
        tool_calls=list(progress.tool_calls),
        created_booking_ids=list(progress.created_booking_ids),
        created_lead_ids=list(progress.created_lead_ids),
        created_handoff_ids=list(progress.created_handoff_ids),
        model_id=(
            turn.version.model_id
            if progress.fallback_model_id is None
            else progress.fallback_model_id
        ),
        input_tokens=LlmTokenCount(progress.input_tokens),
        output_tokens=LlmTokenCount(progress.output_tokens),
        llm_round_count=LlmRoundCount(progress.rounds_used),
        is_fallback_model=progress.is_fallback_model,
    )
