import logging

from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversation_engine import ReplyFailureKind, TurnGate
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.dto.conversation_engine import (
    GeneratedReply,
    PreparedTurn,
    ReplyRecord,
)
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.utilities.conversations.assistant_texts.notice_texts import (
    COLLEAGUE_TAKES_OVER,
    COLLEAGUE_WILL_CALL_BACK,
    CONTACT_LIMIT_NOTICE,
)
from app.utilities.conversations.farewells import is_farewell
from app.utilities.observability.log_context import bound_log_context

LOGGER: logging.Logger = logging.getLogger(__name__)
MAX_QUOTED_CUSTOMER_TEXT: int = 300
FAILURE_HANDOFF_REASONS: dict[ReplyFailureKind, HandoffReason] = {
    ReplyFailureKind.REFUSAL: HandoffReason.SENSITIVE_TOPIC,
    ReplyFailureKind.PROVIDER_ERROR: HandoffReason.NON_STANDARD_REQUEST,
    ReplyFailureKind.NO_ANSWER: HandoffReason.NON_STANDARD_REQUEST,
    ReplyFailureKind.UNVERIFIED_NUMBERS: HandoffReason.UNVERIFIED_NUMBERS,
}
FAILURE_SUMMARIES: dict[ReplyFailureKind, str] = {
    ReplyFailureKind.REFUSAL: "The AI model declined to answer this message.",
    ReplyFailureKind.PROVIDER_ERROR: "The AI model was unavailable.",
    ReplyFailureKind.NO_ANSWER: "The assistant could not finish an answer.",
    ReplyFailureKind.UNVERIFIED_NUMBERS: (
        "The assistant's answer contained values missing from the business data"
    ),
}


class ConversationTurnOrchestrator(ConversationTurnOrchestratorContract):
    """
    Answer one customer message (concept section 1, "path of a message").

    Prepare the turn (business, contact, conversation pinned to a version,
    language, inbound message); while staff own the conversation stay silent
    in chat and promise a call back on the phone; past the contact's message
    limit answer once with a polite stop message. Otherwise generate the
    reply with tools and the invented-numbers guard. When the model refuses,
    is unavailable, cannot finish or keeps unverified numbers, the
    conversation goes to a colleague (unless the model already handed it
    over) and the customer hears so in their language. Finally the reply is
    stored with its usage; on the phone the call ends after a handoff or the
    caller's goodbye.
    """

    def __init__(
        self,
        prepare_turn: UseCaseContract[InboundMessage, PreparedTurn],
        generate_reply: UseCaseContract[PreparedTurn, GeneratedReply],
        handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult],
        record_reply: UseCaseContract[ReplyRecord, AssistantReply],
        localized_text_resolver: LocalizedTextResolverContract,
        storage_scope: StorageScopeContract,
    ) -> None:
        self._prepare_turn: UseCaseContract[InboundMessage, PreparedTurn] = prepare_turn
        self._generate_reply: UseCaseContract[PreparedTurn, GeneratedReply] = (
            generate_reply
        )
        self._handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult] = (
            handoff_to_human
        )
        self._record_reply: UseCaseContract[ReplyRecord, AssistantReply] = record_reply
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._storage_scope: StorageScopeContract = storage_scope

    def execute(self, input_data: InboundMessage) -> AssistantReply:
        # The whole turn, the model's tool calls included, sees only this
        # business's rows (row-level security on Postgres); its log lines
        # name the business, channel and (once known) the conversation.
        with (
            bound_log_context(
                business_id=input_data.business_id, channel=input_data.channel
            ),
            self._storage_scope.scoped_to_business(input_data.business_id),
        ):
            turn: PreparedTurn = self._prepare_turn.run(input_data)
            with bound_log_context(conversation_id=turn.conversation.id):
                return self._answer(turn)

    def _answer(self, turn: PreparedTurn) -> AssistantReply:
        is_phone: bool = turn.conversation.channel is ChannelKind.PHONE
        if turn.gate is not TurnGate.ANSWER:
            return self._record_reply.run(self._build_gated_record(turn, is_phone))

        generated: GeneratedReply = self._generate_reply.run(turn)
        text: MessageText | None = generated.text
        handoff_ids: list[HandoffId] = list(generated.created_handoff_ids)
        if generated.failure is not None:
            text, engine_handoff_id = self._hand_over(turn, generated)
            if engine_handoff_id is not None:
                handoff_ids.append(engine_handoff_id)

        is_handed_off: bool = bool(handoff_ids)
        return self._record_reply.run(
            ReplyRecord(
                turn=turn,
                text=text,
                guard_verdict=generated.guard_verdict,
                tool_calls=list(generated.tool_calls),
                created_booking_ids=list(generated.created_booking_ids),
                created_lead_ids=list(generated.created_lead_ids),
                created_handoff_ids=handoff_ids,
                model_id=generated.model_id,
                input_tokens=generated.input_tokens,
                output_tokens=generated.output_tokens,
                is_handed_off=is_handed_off,
                should_end_call=is_phone
                and (is_handed_off or is_farewell(str(turn.customer_text))),
            )
        )

    def _build_gated_record(self, turn: PreparedTurn, is_phone: bool) -> ReplyRecord:
        if turn.gate is TurnGate.STAFF_CALLBACK:
            return ReplyRecord(
                turn=turn,
                text=self._resolve(COLLEAGUE_WILL_CALL_BACK, turn),
                is_handed_off=True,
                should_end_call=True,
            )

        if turn.gate is TurnGate.LIMIT_NOTICE:
            return ReplyRecord(
                turn=turn,
                text=self._resolve(CONTACT_LIMIT_NOTICE, turn),
                should_end_call=is_phone,
            )

        return ReplyRecord(
            turn=turn,
            is_handed_off=turn.gate is TurnGate.STAFF_SILENCE,
            should_end_call=is_phone,
        )

    def _hand_over(
        self,
        turn: PreparedTurn,
        generated: GeneratedReply,
    ) -> tuple[MessageText, HandoffId | None]:
        """
        Pass the conversation to staff after a failed reply. When the model
        already called handoff_to_human in this turn, no second handoff is
        created; when the handoff cannot be created, the customer still hears
        that a colleague will answer and the error is logged.
        """

        fallback_text: MessageText = self._resolve(COLLEAGUE_TAKES_OVER, turn)
        if generated.created_handoff_ids or generated.failure is None:
            return fallback_text, None

        try:
            result: HandoffResult = self._handoff_to_human.run(
                HandoffCommand(
                    business_id=turn.business.id,
                    conversation_id=turn.conversation.id,
                    contact_id=turn.contact.id,
                    reason=FAILURE_HANDOFF_REASONS[generated.failure],
                    summary=build_failure_summary(turn, generated),
                    urgency=HandoffUrgency.NORMAL,
                    source_channel=turn.conversation.channel,
                    language=turn.language,
                    is_sandbox=turn.conversation.is_sandbox,
                )
            )
        except ApplicationError:
            LOGGER.exception("Handoff of conversation %s failed.", turn.conversation.id)
            return fallback_text, None

        return result.customer_message, result.id

    def _resolve(self, text: LocalizedText, turn: PreparedTurn) -> MessageText:
        return MessageText(self._localized_text_resolver.resolve(text, turn.language))


def build_failure_summary(
    turn: PreparedTurn, generated: GeneratedReply
) -> HandoffSummary:
    """Summary for staff: what went wrong and what the customer wrote."""

    failure: ReplyFailureKind = (
        ReplyFailureKind.NO_ANSWER if generated.failure is None else generated.failure
    )
    details: str = FAILURE_SUMMARIES[failure]
    if generated.unverified_values:
        details += ": " + ", ".join(str(value) for value in generated.unverified_values)

    customer_text: str = str(turn.customer_text)[:MAX_QUOTED_CUSTOMER_TEXT]
    return HandoffSummary(f"{details.rstrip('.')}. Customer wrote: «{customer_text}»")
