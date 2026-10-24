from collections.abc import Callable

from typed_time_provider import Microseconds, WallClock

from app.contracts.brain import AssistantToolRegistryContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.reply_safety import ClaimCheckFacilitatorContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    LlmTurnRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.conversation_engine import ReplyFailureKind
from app.schemas.constants.conversations import LlmTurnRole
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
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    MessageText,
)
from app.use_cases.conversations.replies.customer_turn import build_customer_turn
from app.use_cases.conversations.replies.guarded_replies import (
    clean_reply,
    handed_off_reply,
    rewritten_reply,
)
from app.use_cases.conversations.replies.reply_review import (
    ReplyReview,
    ReplyReviewer,
)
from app.use_cases.conversations.replies.transcript_turns import (
    append_response,
    append_turn,
)
from app.use_cases.conversations.replies.turn_progress import (
    TurnProgress,
    build_reply,
    record_response,
    record_tool_outcome,
    start_progress,
)
from app.utilities.conversations.customer_text_fencing import new_fence_key
from app.utilities.conversations.guard_rewrite_note import build_guard_rewrite_note


class GenerateAssistantReplyUseCase(UseCaseContract[PreparedTurn, GeneratedReply]):
    """
    Ask the pinned assistant version for a reply (concept sections 1 and 5).

    The customer's message is appended to the verbatim transcript as one
    user turn: the server context line, then the text (voice notes as their
    transcripts, places as coordinates, photos shown as pictures), preceded
    by what the customer wrote while the assistant stayed silent (a handoff,
    the hourly limit), so the model never loses those messages. Customer text is
    fenced with a key that is new for every turn and cannot imitate the
    platform's lines (`customer_text_fencing`). The model may call
    the offered tools for up to `tool_round_limit` rounds; all results of a
    round go back in one tool-results turn. Every turn gets the next
    sequence number and is only ever appended.

    The final text passes the reply guard (`ReplyReviewer`): values missing
    from the facts, the conversation's tool results and the context (and,
    except for prices and percentages, from the customer's messages),
    policy and availability claims the claim check's verifier finds
    unsupported, and another person's phone number or e-mail address are
    sent back once with a request to rewrite; a reply that still has them
    is replaced by a handoff (failure PERSONAL_DATA, UNVERIFIED_NUMBERS or
    UNSUPPORTED_CLAIM). A refusal, a provider error or no answer within the
    round limit are failures too; the engine then passes the conversation
    to a colleague.
    """

    def __init__(
        self,
        llm_adapter: LlmAdapterContract,
        llm_turn_repo: LlmTurnRepoContract,
        message_repo: MessageRepoContract,
        contact_repo: ContactRepoContract,
        claim_check: ClaimCheckFacilitatorContract,
        tool_registry: AssistantToolRegistryContract,
        run_assistant_tool: UseCaseContract[
            AssistantToolInvocation, AssistantToolOutcome
        ],
        wall_clock: WallClock[Microseconds],
        max_output_tokens: LlmMaxOutputTokens,
        effort: LlmEffort,
        tool_round_limit: LlmToolRoundLimit,
        fence_key_factory: Callable[[], str] = new_fence_key,
    ) -> None:
        self._llm_adapter: LlmAdapterContract = llm_adapter
        self._llm_turn_repo: LlmTurnRepoContract = llm_turn_repo
        self._message_repo: MessageRepoContract = message_repo
        self._reviewer: ReplyReviewer = ReplyReviewer(
            message_repo, contact_repo, claim_check
        )
        self._tool_registry: AssistantToolRegistryContract = tool_registry
        self._run_assistant_tool: UseCaseContract[
            AssistantToolInvocation, AssistantToolOutcome
        ] = run_assistant_tool
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._max_output_tokens: LlmMaxOutputTokens = max_output_tokens
        self._effort: LlmEffort = effort
        self._tool_round_limit: LlmToolRoundLimit = tool_round_limit
        self._fence_key_factory: Callable[[], str] = fence_key_factory

    def run(self, input_data: PreparedTurn) -> GeneratedReply:
        stored_turns: list[LlmTurnDocument] = self._llm_turn_repo.list_by_conversation(
            input_data.conversation.id
        )
        progress: TurnProgress = start_progress(stored_turns)
        tools: list[LlmToolDefinition] = self._tool_registry.list_definitions(
            list(input_data.tool_context.available_tools)
        )
        self._append(
            input_data,
            progress,
            LlmTurnRole.USER,
            build_customer_turn(
                self._llm_adapter,
                self._message_repo,
                input_data,
                stored_turns,
                self._fence_key_factory(),
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

        review: ReplyReview = self._reviewer.review(input_data, progress, text)
        if not review.reasons:
            return clean_reply(input_data, progress, text, review)

        return self._rewrite_once(input_data, tools, progress, review)

    def _rewrite_once(
        self,
        turn: PreparedTurn,
        tools: list[LlmToolDefinition],
        progress: TurnProgress,
        first: ReplyReview,
    ) -> GeneratedReply:
        self._append(
            turn,
            progress,
            LlmTurnRole.USER,
            self._llm_adapter.build_user_text_turn(
                MessageText(
                    build_guard_rewrite_note(
                        [str(value) for value in first.unverified_values],
                        [str(finding.claim) for finding in first.unsupported_claims],
                        first.withheld_details,
                    )
                )
            ),
        )
        rewritten_text: MessageText | None = None
        try:
            rewritten_text = self._run_rounds(turn, tools, progress)
        except ExternalServiceError:
            rewritten_text = None

        if rewritten_text is None or str(rewritten_text).strip() == "":
            return handed_off_reply(turn, progress, first, None)

        second: ReplyReview = self._reviewer.review(turn, progress, rewritten_text)
        if second.reasons:
            return handed_off_reply(turn, progress, first, second)

        return rewritten_reply(turn, progress, rewritten_text, first, second)

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
                    fallback_transcript=list(progress.canonical_transcript),
                )
            )
            record_response(progress, response)
            append_response(
                self._llm_turn_repo, self._wall_clock, turn, progress, response
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
        append_turn(
            self._llm_turn_repo, self._wall_clock, turn, progress, role, payload
        )
