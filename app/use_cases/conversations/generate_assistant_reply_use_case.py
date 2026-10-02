from dataclasses import dataclass, field

from typed_time_provider import Microseconds, WallClock

from app.contracts.brain import AssistantToolRegistryContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.repositories.conversation_repositories import (
    LlmTurnRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversation_engine import ReplyFailureKind
from app.schemas.constants.conversations import (
    LlmTurnRole,
    MessageAuthor,
    ReplyGuardVerdict,
)
from app.schemas.domain.conversations import LlmTurnDocument, ToolCallRecord
from app.schemas.dto.assistant_tools import (
    AssistantToolInvocation,
    AssistantToolOutcome,
)
from app.schemas.dto.conversation_engine import GeneratedReply, PreparedTurn
from app.schemas.dto.conversations import (
    LlmRequest,
    LlmResponse,
    LlmToolCall,
    LlmToolDefinition,
    LlmToolResult,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.assistants.constrained_integers import (
    LlmMaxOutputTokens,
    LlmToolRoundLimit,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.conversations.constrained_integers import (
    LlmTokenCount,
    LlmTurnSequenceNumber,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.utilities.conversations.turn_context import (
    EarlierMessage,
    build_rewrite_note,
    build_text_with_unanswered_messages,
    build_user_turn_text,
)
from app.utilities.reply_guard.invented_numbers import find_unverified_values


@dataclass
class _TurnProgress:
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


class GenerateAssistantReplyUseCase(UseCaseContract[PreparedTurn, GeneratedReply]):
    """
    Ask the pinned assistant version for a reply (concept sections 1 and 5).

    The customer's message is appended to the verbatim transcript as one
    user turn: the server context line, then the text, preceded by what the
    customer wrote while the assistant stayed silent (a handoff, the hourly
    limit), so the model never loses those messages. The model may call
    the offered tools for up to `tool_round_limit` rounds; all results of a
    round go back in one tool-results turn. Every turn gets the next
    sequence number and is only ever appended.

    The final text passes the invented-numbers guard: values missing from the
    facts, the conversation's tool results and the context (and, except for
    prices and percentages, from the customer's messages) are sent back once
    with a request to rewrite; a reply that still has them is replaced by a
    handoff (failure UNVERIFIED_NUMBERS). A refusal,
    a provider error or no answer within the round limit are failures too;
    the engine then passes the conversation to a colleague.
    """

    def __init__(
        self,
        llm_adapter: LlmAdapterContract,
        llm_turn_repo: LlmTurnRepoContract,
        message_repo: MessageRepoContract,
        tool_registry: AssistantToolRegistryContract,
        run_assistant_tool: UseCaseContract[
            AssistantToolInvocation, AssistantToolOutcome
        ],
        wall_clock: WallClock[Microseconds],
        max_output_tokens: LlmMaxOutputTokens,
        effort: LlmEffort,
        tool_round_limit: LlmToolRoundLimit,
    ) -> None:
        self._llm_adapter: LlmAdapterContract = llm_adapter
        self._llm_turn_repo: LlmTurnRepoContract = llm_turn_repo
        self._message_repo: MessageRepoContract = message_repo
        self._tool_registry: AssistantToolRegistryContract = tool_registry
        self._run_assistant_tool: UseCaseContract[
            AssistantToolInvocation, AssistantToolOutcome
        ] = run_assistant_tool
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._max_output_tokens: LlmMaxOutputTokens = max_output_tokens
        self._effort: LlmEffort = effort
        self._tool_round_limit: LlmToolRoundLimit = tool_round_limit

    def run(self, input_data: PreparedTurn) -> GeneratedReply:
        stored_turns: list[LlmTurnDocument] = self._llm_turn_repo.list_by_conversation(
            input_data.conversation.id
        )
        progress = _TurnProgress(
            transcript=[turn.payload for turn in stored_turns],
            next_sequence_number=(
                0 if not stored_turns else int(stored_turns[-1].sequence_number) + 1
            ),
        )
        tools: list[LlmToolDefinition] = self._tool_registry.list_definitions(
            list(input_data.tool_context.available_tools)
        )
        self._append(
            input_data,
            progress,
            LlmTurnRole.USER,
            self._llm_adapter.build_user_text_turn(
                MessageText(
                    build_user_turn_text(
                        str(input_data.context_line),
                        build_text_with_unanswered_messages(
                            self._collect_unanswered_messages(input_data, stored_turns),
                            str(input_data.customer_text),
                        ),
                    )
                )
            ),
        )
        try:
            text: MessageText | None = self._run_rounds(input_data, tools, progress)
        except LlmRefusedError:
            return build_reply(input_data, progress, failure=ReplyFailureKind.REFUSAL)
        except ExternalServiceError:
            return build_reply(
                input_data, progress, failure=ReplyFailureKind.PROVIDER_ERROR
            )

        if text is None or str(text).strip() == "":
            return build_reply(input_data, progress, failure=ReplyFailureKind.NO_ANSWER)

        unverified_values: list[UnverifiedReplyValue] = self._check_numbers(
            input_data, progress, text
        )
        if not unverified_values:
            return build_reply(input_data, progress, text=text)

        return self._rewrite_once(input_data, tools, progress, unverified_values)

    def _collect_unanswered_messages(
        self,
        turn: PreparedTurn,
        stored_turns: list[LlmTurnDocument],
    ) -> list[EarlierMessage]:
        """
        Messages after the last model turn and before this one: the customer
        messages the assistant stayed silent on (handoff, hourly limit) and
        what staff wrote meanwhile, which the model never saw otherwise.
        """

        last_turn_at: int = int(stored_turns[-1].created_at) if stored_turns else -1
        return [
            EarlierMessage(
                text=str(message.text),
                is_from_staff=message.author is MessageAuthor.STAFF,
            )
            for message in sorted(
                self._message_repo.list_by_conversation(
                    turn.business.id, turn.conversation.id
                ),
                key=lambda message: int(message.created_at),
            )
            if (
                message.direction is MessageDirection.INBOUND
                or message.author is MessageAuthor.STAFF
            )
            and last_turn_at < int(message.created_at) < int(turn.received_at)
        ]

    def _rewrite_once(
        self,
        turn: PreparedTurn,
        tools: list[LlmToolDefinition],
        progress: _TurnProgress,
        unverified_values: list[UnverifiedReplyValue],
    ) -> GeneratedReply:
        self._append(
            turn,
            progress,
            LlmTurnRole.USER,
            self._llm_adapter.build_user_text_turn(
                MessageText(
                    build_rewrite_note([str(value) for value in unverified_values])
                )
            ),
        )
        rewritten_text: MessageText | None = None
        try:
            rewritten_text = self._run_rounds(turn, tools, progress)
        except ExternalServiceError:
            rewritten_text = None

        is_rewritten: bool = (
            rewritten_text is not None and str(rewritten_text).strip() != ""
        )
        remaining_values: list[UnverifiedReplyValue] = (
            self._check_numbers(turn, progress, rewritten_text)
            if rewritten_text is not None and is_rewritten
            else unverified_values
        )
        if rewritten_text is None or not is_rewritten or remaining_values:
            return build_reply(
                turn,
                progress,
                failure=ReplyFailureKind.UNVERIFIED_NUMBERS,
                guard_verdict=ReplyGuardVerdict.HANDED_OFF,
                unverified_values=remaining_values,
            )

        return build_reply(
            turn,
            progress,
            text=rewritten_text,
            guard_verdict=ReplyGuardVerdict.REWRITTEN,
            unverified_values=unverified_values,
        )

    def _run_rounds(
        self,
        turn: PreparedTurn,
        tools: list[LlmToolDefinition],
        progress: _TurnProgress,
    ) -> MessageText | None:
        """
        Call the model until it answers without tools; None when the round
        limit is spent (a rewrite gets at least one more call).
        """

        while True:
            response: LlmResponse = self._llm_adapter.complete(
                LlmRequest(
                    model_id=turn.version.model_id,
                    system_prompt=turn.version.prompt_text,
                    tools=tools,
                    transcript=list(progress.transcript),
                    max_output_tokens=self._max_output_tokens,
                    effort=self._effort,
                )
            )
            progress.rounds_used += 1
            progress.input_tokens += int(response.input_tokens)
            progress.output_tokens += int(response.output_tokens)
            self._append(
                turn,
                progress,
                LlmTurnRole.ASSISTANT,
                response.assistant_turn_payload,
            )
            if not response.tool_calls:
                return response.text

            results: list[LlmToolResult] = [
                self._run_tool(turn, progress, call) for call in response.tool_calls
            ]
            self._append(
                turn,
                progress,
                LlmTurnRole.USER,
                self._llm_adapter.build_tool_results_turn(results),
            )
            if progress.rounds_used >= int(self._tool_round_limit):
                return None

    def _run_tool(
        self,
        turn: PreparedTurn,
        progress: _TurnProgress,
        call: LlmToolCall,
    ) -> LlmToolResult:
        outcome: AssistantToolOutcome = self._run_assistant_tool.run(
            AssistantToolInvocation(context=turn.tool_context, call=call)
        )
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

        return outcome.result

    def _check_numbers(
        self,
        turn: PreparedTurn,
        progress: _TurnProgress,
        text: MessageText,
    ) -> list[UnverifiedReplyValue]:
        # Trusted: what the business and the server said.
        evidence: list[str] = [
            str(turn.business.name),
            str(turn.context_line),
            *(f"{fact.label}: {fact.value}" for fact in turn.version.facts),
            *progress.tool_results,
        ]
        # What the customer wrote, and earlier replies (which may repeat it):
        # they back times, dates, phones and counts, never a price.
        customer_texts: list[str] = []
        for message in self._message_repo.list_by_conversation(
            turn.business.id, turn.conversation.id
        ):
            if message.direction is MessageDirection.INBOUND:
                customer_texts.append(str(message.text))
                continue

            if message.author is MessageAuthor.ASSISTANT:
                customer_texts.append(str(message.text))

            # Staff are the business speaking: the assistant may repeat their
            # prices and terms.
            if message.author is MessageAuthor.STAFF:
                evidence.append(str(message.text))

            # Tool results of earlier replies and of voice-agent calls count.
            evidence.extend(
                str(record.result_json)
                for record in message.tool_calls
                if not record.is_error
            )

        return find_unverified_values(
            text,
            evidence,
            [*turn.version.languages, turn.language],
            [turn.business.currency_code],
            customer_texts=customer_texts,
        )

    def _append(
        self,
        turn: PreparedTurn,
        progress: _TurnProgress,
        role: LlmTurnRole,
        payload: LlmProviderPayload,
    ) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        self._llm_turn_repo.append(
            LlmTurnDocument(
                conversation_id=turn.conversation.id,
                sequence_number=LlmTurnSequenceNumber(progress.next_sequence_number),
                role=role,
                payload=payload,
                created_at=now,
                updated_at=now,
            )
        )
        progress.transcript.append(payload)
        progress.next_sequence_number += 1


def build_reply(
    turn: PreparedTurn,
    progress: _TurnProgress,
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
