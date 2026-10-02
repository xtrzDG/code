"""What one reply turn produced so far, and the reply it becomes."""

from dataclasses import dataclass, field

from app.schemas.constants.conversation_engine import ReplyFailureKind
from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.domain.conversations import ToolCallRecord
from app.schemas.dto.assistant_tools import AssistantToolOutcome
from app.schemas.dto.conversation_engine import GeneratedReply, PreparedTurn
from app.schemas.dto.conversations import LlmToolCall
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId


@dataclass
class TurnProgress:
    """What one turn produced so far (mutable technical state of the loop)."""

    transcript: list[LlmProviderPayload]
    next_sequence_number: int
    tool_calls: list[ToolCallRecord] = field(default_factory=list[ToolCallRecord])
    tool_results: list[str] = field(default_factory=list[str])
    created_booking_ids: list[BookingId] = field(default_factory=list[BookingId])
    created_lead_ids: list[LeadId] = field(default_factory=list[LeadId])
    created_handoff_ids: list[HandoffId] = field(default_factory=list[HandoffId])
    input_tokens: int = 0
    output_tokens: int = 0
    rounds_used: int = 0


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
) -> GeneratedReply:
    return GeneratedReply(
        text=text,
        failure=failure,
        guard_verdict=guard_verdict,
        unverified_values=[] if unverified_values is None else unverified_values,
        tool_calls=list(progress.tool_calls),
        created_booking_ids=list(progress.created_booking_ids),
        created_lead_ids=list(progress.created_lead_ids),
        created_handoff_ids=list(progress.created_handoff_ids),
        model_id=turn.version.model_id,
        input_tokens=LlmTokenCount(progress.input_tokens),
        output_tokens=LlmTokenCount(progress.output_tokens),
    )
