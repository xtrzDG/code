from typed_time_provider import Microseconds, WallClock

from app.contracts.brain import AssistantToolRegistryContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.repositories.conversation_repositories import (
    LlmTurnRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.conversation_engine import ReplyFailureKind
from app.schemas.constants.conversations import (
    LlmTurnRole,
    ReplyGuardVerdict,
)
from app.schemas.domain.conversations import LlmTurnDocument
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
from app.schemas.typings.conversations.constrained_integers import (
    LlmTurnSequenceNumber,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    MessageText,
    UnverifiedReplyValue,
)
from app.use_cases.conversations.replies.reply_evidence import (
    collect_unanswered_messages,
    find_unverified_reply_values,
)
from app.use_cases.conversations.replies.turn_progress import (
    TurnProgress,
    build_reply,
    record_tool_outcome,
)
from app.utilities.conversations.turn_context import (
    build_rewrite_note,
    build_text_with_unanswered_messages,
    build_user_turn_text,
)


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
        progress = TurnProgress(
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
                            collect_unanswered_messages(
                                self._message_repo, input_data, stored_turns
                            ),
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

        unverified_values: list[UnverifiedReplyValue] = find_unverified_reply_values(
            self._message_repo, input_data, progress, text
        )
        if not unverified_values:
            return build_reply(input_data, progress, text=text)

        return self._rewrite_once(input_data, tools, progress, unverified_values)

    def _rewrite_once(
        self,
        turn: PreparedTurn,
        tools: list[LlmToolDefinition],
        progress: TurnProgress,
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
            find_unverified_reply_values(
                self._message_repo, turn, progress, rewritten_text
            )
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
        progress: TurnProgress,
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
        progress: TurnProgress,
        call: LlmToolCall,
    ) -> LlmToolResult:
        outcome: AssistantToolOutcome = self._run_assistant_tool.run(
            AssistantToolInvocation(context=turn.tool_context, call=call)
        )
        record_tool_outcome(progress, call, outcome)
        return outcome.result

    def _append(
        self,
        turn: PreparedTurn,
        progress: TurnProgress,
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
