import logging

from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.conversations.failure_handoffs import (
    FAILURE_HANDOFF_REASONS,
    build_failure_summary,
)
from app.orchestrators.conversations.spend_brake import (
    SpendCheck,
    check_turn_spend,
    on_cheaper_model,
    paused_reply,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.handoffs import HandoffUrgency
from app.schemas.constants.spend import SpendLevel
from app.schemas.dto.conversation_engine import (
    GeneratedReply,
    PreparedTurn,
    ReplyRecord,
)
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.feedback.customer_signals import CustomerSignalReply
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.utilities.conversations.assistant_texts.attachment_notice_texts import (
    CANNOT_READ_ATTACHMENT,
)
from app.utilities.conversations.assistant_texts.notice_texts import (
    COLLEAGUE_TAKES_OVER,
    COLLEAGUE_WILL_CALL_BACK,
    CONTACT_LIMIT_NOTICE,
)
from app.utilities.conversations.farewells import is_farewell
from app.utilities.observability.log_context import bound_log_context

LOGGER: logging.Logger = logging.getLogger(__name__)


class ConversationTurnOrchestrator(ConversationTurnOrchestratorContract):
    """
    Answer one customer message (concept section 1, "path of a message").

    Prepare the turn (business, contact, conversation pinned to a version,
    language, inbound message); a customer's STOP, START or visit rating is
    answered by the platform (and a low rating handed to a colleague)
    without the model; while staff own the conversation stay silent
    in chat and promise a call back on the phone; past the contact's message
    limit answer once with a polite stop message; a message with nothing the
    assistant can read (a sticker, a file) gets a polite request to write.
    Otherwise generate the reply with tools and the reply guard (numbers,
    claims, other people's contact details). When the model refuses, is
    unavailable, cannot finish or keeps what the guard holds back, the
    conversation goes to a colleague (unless the model already handed it
    over) and the customer hears so in their language. Before the model is
    asked, the spend guard checks the business's spend of its day: past
    its soft limit the turn uses a cheaper model, past its hard limit the
    conversation goes to the team without a model call (`spend_brake`).
    Finally the reply is stored with its usage; on the phone the call ends
    after a handoff or the caller's goodbye.
    """

    def __init__(
        self,
        prepare_turn: UseCaseContract[InboundMessage, PreparedTurn],
        generate_reply: UseCaseContract[PreparedTurn, GeneratedReply],
        handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult],
        record_reply: UseCaseContract[ReplyRecord, AssistantReply],
        localized_text_resolver: LocalizedTextResolverContract,
        storage_scope: StorageScopeContract,
        answer_customer_signal: UseCaseContract[
            PreparedTurn, CustomerSignalReply | None
        ],
        check_spend: SpendCheck | None = None,
        answer_waitlist_offer: UseCaseContract[PreparedTurn, CustomerSignalReply | None]
        | None = None,
    ) -> None:
        self._answer_waitlist_offer: (
            UseCaseContract[PreparedTurn, CustomerSignalReply | None] | None
        ) = answer_waitlist_offer
        self._check_spend: SpendCheck | None = check_spend
        self._answer_customer_signal: UseCaseContract[
            PreparedTurn, CustomerSignalReply | None
        ] = answer_customer_signal
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
            with bound_log_context(
                conversation_id=turn.conversation.id,
                contact_id=turn.conversation.contact_id,
            ):
                record: ReplyRecord = self._answer(turn, input_data.is_reply_deferred)
                return self._record_reply.run(
                    record.model_copy(
                        update={"waiting_since": input_data.waiting_since}
                    )
                )

    def _answer(self, turn: PreparedTurn, is_reply_deferred: bool) -> ReplyRecord:
        """
        What to store for the turn. A message the customer followed up
        right away is only stored (unless it is a signal the platform
        answers): the next message's reply answers both.
        """

        is_phone: bool = turn.conversation.channel is ChannelKind.PHONE
        signal: CustomerSignalReply | None = self._answer_customer_signal.run(turn)
        if signal is None and self._answer_waitlist_offer is not None:
            # A yes or no to a place the waitlist offered (books under lock).
            signal = self._answer_waitlist_offer.run(turn)
        if signal is not None:
            return self._build_signal_record(turn, signal)

        if is_reply_deferred:
            return ReplyRecord(
                turn=turn, is_handed_off=turn.gate is TurnGate.STAFF_SILENCE
            )

        if turn.gate is not TurnGate.ANSWER:
            return self._build_gated_record(turn, is_phone)

        verdict = check_turn_spend(self._check_spend, turn)
        if verdict is not None and verdict.level is SpendLevel.HARD_LIMIT:
            generated: GeneratedReply = paused_reply(turn)
        else:
            turn = on_cheaper_model(turn, verdict)
            generated = self._generate_reply.run(turn)
        text: MessageText | None = generated.text
        handoff_ids: list[HandoffId] = list(generated.created_handoff_ids)
        if generated.failure is not None:
            text, engine_handoff_id = self._hand_over(turn, generated)
            if engine_handoff_id is not None:
                handoff_ids.append(engine_handoff_id)

        is_handed_off: bool = bool(handoff_ids)
        return ReplyRecord(
            turn=turn,
            text=text,
            guard_verdict=generated.guard_verdict,
            guard_reasons=list(generated.guard_reasons),
            unverified_values=list(generated.unverified_values),
            claim_findings=list(generated.claim_findings),
            verifier_usage=list(generated.verifier_usage),
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
            llm_round_count=generated.llm_round_count,
            is_fallback_model=generated.is_fallback_model,
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

        if turn.gate is TurnGate.ATTACHMENT_NOTICE:
            return ReplyRecord(
                turn=turn, text=self._resolve(CANNOT_READ_ATTACHMENT, turn)
            )

        return ReplyRecord(
            turn=turn,
            is_handed_off=turn.gate is TurnGate.STAFF_SILENCE,
            should_end_call=is_phone,
        )

    def _build_signal_record(
        self, turn: PreparedTurn, signal: CustomerSignalReply
    ) -> ReplyRecord:
        """
        The platform's answer to a signal; a low visit rating also opens
        its handoff (a failure is logged: the customer is still thanked).
        """

        handoff_ids: list[HandoffId] = []
        if signal.handoff is not None:
            try:
                handoff_ids.append(self._handoff_to_human.run(signal.handoff).id)
            except ApplicationError:
                LOGGER.exception(
                    "Handoff after a visit rating in %s failed.", turn.conversation.id
                )

        return ReplyRecord(
            turn=turn,
            text=signal.text,
            created_handoff_ids=handoff_ids,
            created_booking_ids=[]
            if signal.booking_id is None
            else [signal.booking_id],
            is_handed_off=bool(handoff_ids),
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
                    language=turn.reply_language,
                    is_sandbox=turn.conversation.is_sandbox,
                )
            )
        except ApplicationError:
            LOGGER.exception("Handoff of conversation %s failed.", turn.conversation.id)
            return fallback_text, None

        return result.customer_message, result.id

    def _resolve(self, text: LocalizedText, turn: PreparedTurn) -> MessageText:
        return MessageText(
            self._localized_text_resolver.resolve(text, turn.reply_language)
        )
