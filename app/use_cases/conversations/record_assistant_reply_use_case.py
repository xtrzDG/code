from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories import (
    ConversationRepoContract,
    MessageRepoContract,
    UsageEventRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.conversation_engine import PreparedTurn, ReplyRecord
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantity,
)
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.conversations.assistant_texts import (
    AI_DISCLOSURE,
    fill_business_name,
)
from app.utilities.conversations.llm_models import LlmCallCost, compute_llm_call_cost

DISCLOSURE_SEPARATOR: str = "\n"


class RecordAssistantReplyUseCase(UseCaseContract[ReplyRecord, AssistantReply]):
    """
    Store the assistant's answer of one turn and account for it.

    The first assistant reply of a chat conversation starts with the
    disclosure "Hello! I am the AI assistant of <business>." in the
    conversation language (phone calls disclose in the call greeting). The
    outbound message keeps the tool calls, model, tokens and cost (from the
    model price table); usage events record input and output tokens and one
    dialog per real conversation. The conversation, re-read because tools
    may have changed it, gets its last message time and the HANDOFF status
    when staff now own it.
    """

    def __init__(
        self,
        message_repo: MessageRepoContract,
        conversation_repo: ConversationRepoContract,
        usage_event_repo: UsageEventRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._message_repo: MessageRepoContract = message_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ReplyRecord) -> AssistantReply:
        turn: PreparedTurn = input_data.turn
        now: Microseconds = self._wall_clock.now_unix()
        disclosure: MessageText | None = self._find_disclosure(turn, input_data.text)
        text: MessageText | None = (
            input_data.text
            if disclosure is None or input_data.text is None
            else MessageText(f"{disclosure}{DISCLOSURE_SEPARATOR}{input_data.text}")
        )
        cost: LlmCallCost = (
            LlmCallCost(CostMicroUsd(0), CostMicroUsd(0))
            if input_data.model_id is None
            else compute_llm_call_cost(
                input_data.model_id,
                input_data.input_tokens,
                input_data.output_tokens,
            )
        )
        if text is not None:
            self._message_repo.save(
                MessageDocument(
                    conversation_id=turn.conversation.id,
                    business_id=turn.business.id,
                    direction=MessageDirection.OUTBOUND,
                    author=MessageAuthor.ASSISTANT,
                    text=text,
                    language=turn.language,
                    tool_calls=list(input_data.tool_calls),
                    model_id=input_data.model_id,
                    input_tokens=input_data.input_tokens,
                    output_tokens=input_data.output_tokens,
                    cost_micro_usd=cost.total,
                    created_at=now,
                    updated_at=now,
                )
            )

        self._record_usage(input_data, cost, now)
        conversation: ConversationDocument = (
            self._conversation_repo.get(turn.business.id, turn.conversation.id)
            or turn.conversation
        )
        is_handed_off: bool = (
            input_data.is_handed_off
            or conversation.status is ConversationStatus.HANDOFF
        )
        if is_handed_off:
            conversation.status = ConversationStatus.HANDOFF

        conversation.last_message_at = now
        conversation.updated_at = now
        self._conversation_repo.save(conversation)
        return AssistantReply(
            conversation_id=conversation.id,
            text=text,
            disclosure_text=disclosure,
            language=turn.language,
            is_handed_off=is_handed_off,
            guard_verdict=input_data.guard_verdict,
            should_end_call=input_data.should_end_call,
            created_booking_ids=list(input_data.created_booking_ids),
            created_lead_ids=list(input_data.created_lead_ids),
            created_handoff_ids=list(input_data.created_handoff_ids),
        )

    def _find_disclosure(
        self,
        turn: PreparedTurn,
        text: MessageText | None,
    ) -> MessageText | None:
        """The AI disclosure that opens the first chat reply, if due."""

        if (
            text is None
            or not turn.is_first_reply
            or turn.conversation.channel is ChannelKind.PHONE
        ):
            return None

        return MessageText(
            fill_business_name(
                self._localized_text_resolver.resolve(AI_DISCLOSURE, turn.language),
                str(turn.business.name),
            )
        )

    def _record_usage(
        self,
        record: ReplyRecord,
        cost: LlmCallCost,
        now: Microseconds,
    ) -> None:
        turn: PreparedTurn = record.turn
        usages: list[tuple[UsageKind, int, CostMicroUsd]] = [
            (UsageKind.LLM_INPUT_TOKENS, int(record.input_tokens), cost.input_cost),
            (UsageKind.LLM_OUTPUT_TOKENS, int(record.output_tokens), cost.output_cost),
        ]
        if turn.is_new_conversation and not turn.conversation.is_sandbox:
            usages.append((UsageKind.DIALOG, 1, CostMicroUsd(0)))

        for kind, quantity, usage_cost in usages:
            if quantity == 0:
                continue

            self._usage_event_repo.append(
                UsageEventDocument(
                    business_id=turn.business.id,
                    conversation_id=turn.conversation.id,
                    kind=kind,
                    quantity=UsageQuantity(quantity),
                    cost_micro_usd=usage_cost,
                    occurred_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
