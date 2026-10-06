from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.billing_repositories import UsageEventRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.service_metrics import ServiceMetricsContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import (
    ConversationStatus,
    MessageAuthor,
    ReplyGuardVerdict,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.conversation_engine import PreparedTurn, ReplyRecord
from app.schemas.dto.conversation_feed.conversation_views import ToolCallView
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.conversations.reply_usage import (
    record_reply_usage,
    total_verifier_cost,
)
from app.utilities.conversations.assistant_texts.ai_disclosure_texts import (
    AI_DISCLOSURE,
)
from app.utilities.conversations.assistant_texts.business_name_placeholder import (
    fill_business_name,
)
from app.utilities.conversations.llm_models import LlmCallCost, compute_llm_call_cost
from app.utilities.conversations.reply_latency import measure_reply_latency
from app.utilities.observability.metrics.null_service_metrics import (
    NO_SERVICE_METRICS,
)
from app.utilities.observability.metrics.observed_durations import (
    milliseconds_as_seconds,
)

DISCLOSURE_SEPARATOR: str = "\n"


class RecordAssistantReplyUseCase(UseCaseContract[ReplyRecord, AssistantReply]):
    """
    Store the assistant's answer of one turn and account for it.

    The first assistant reply of a chat conversation starts with the
    disclosure "Hello! I am the AI assistant of <business>." in the language
    the customer writes in, also one the business did not list
    (`reply_language`; phone calls disclose in the call greeting). The
    outbound message keeps the tool calls, model, tokens and cost (from the
    model price table, the claim check's verifier included) and what the
    reply guard did (verdict, reasons, flagged values, checked claims; only
    for a model's reply); usage events record input and output tokens and
    one dialog per real conversation. The conversation, re-read because tools
    may have changed it, gets its last message time and the HANDOFF status
    when staff now own it. The reply names the version that answered and
    carries the turn's tool calls. A real customer's measured wait is
    observed for /metrics (answer latency by channel; test chats are not).
    """

    def __init__(
        self,
        message_repo: MessageRepoContract,
        conversation_repo: ConversationRepoContract,
        usage_event_repo: UsageEventRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        metrics: ServiceMetricsContract = NO_SERVICE_METRICS,
    ) -> None:
        self._metrics: ServiceMetricsContract = metrics
        self._message_repo: MessageRepoContract = message_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events

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
        reply_latency: ReplyLatencyMilliseconds | None = measure_reply_latency(
            input_data.waiting_since, now
        )
        if text is not None:
            self._observe_answer_latency(turn, reply_latency)
            self._message_repo.save(
                MessageDocument(
                    # The id the inbox chose: the reply it sends is this one.
                    id=turn.reply_message_id or MessageId(),
                    conversation_id=turn.conversation.id,
                    business_id=turn.business.id,
                    direction=MessageDirection.OUTBOUND,
                    author=MessageAuthor.ASSISTANT,
                    text=text,
                    language=turn.reply_language,
                    tool_calls=list(input_data.tool_calls),
                    model_id=input_data.model_id,
                    input_tokens=input_data.input_tokens,
                    output_tokens=input_data.output_tokens,
                    cost_micro_usd=CostMicroUsd(
                        int(cost.total) + int(total_verifier_cost(input_data))
                    ),
                    channel=turn.conversation.channel,
                    reply_latency_ms=reply_latency,
                    llm_round_count=input_data.llm_round_count,
                    is_fallback_model=input_data.is_fallback_model,
                    guard_verdict=guard_verdict_of(input_data),
                    guard_reasons=list(input_data.guard_reasons),
                    unverified_values=list(input_data.unverified_values),
                    claim_findings=list(input_data.claim_findings),
                    created_at=now,
                    updated_at=now,
                )
            )

        record_reply_usage(self._usage_event_repo, input_data, cost, now)
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
        self._live_events.publish(
            conversation.business_id,
            LiveEventKind.CONVERSATION_MESSAGE,
            (conversation.id,),
            is_sandbox=conversation.is_sandbox,
        )
        return AssistantReply(
            conversation_id=conversation.id,
            text=text,
            disclosure_text=disclosure,
            language=turn.reply_language,
            is_handed_off=is_handed_off,
            guard_verdict=input_data.guard_verdict,
            should_end_call=input_data.should_end_call,
            created_booking_ids=list(input_data.created_booking_ids),
            created_lead_ids=list(input_data.created_lead_ids),
            created_handoff_ids=list(input_data.created_handoff_ids),
            assistant_version_id=turn.version.id,
            assistant_version_number=turn.version.version_number,
            tool_calls=[
                ToolCallView(
                    tool_name=record.tool_name,
                    input_json=record.input_json,
                    result_json=record.result_json,
                    is_error=record.is_error,
                )
                for record in input_data.tool_calls
            ],
        )

    def _observe_answer_latency(
        self, turn: PreparedTurn, latency: ReplyLatencyMilliseconds | None
    ) -> None:
        if latency is not None and not turn.conversation.is_sandbox:
            self._metrics.observe_answer_latency(
                turn.conversation.channel, milliseconds_as_seconds(int(latency))
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
                self._localized_text_resolver.resolve(
                    AI_DISCLOSURE, turn.reply_language
                ),
                str(turn.business.name),
            )
        )


def guard_verdict_of(record: ReplyRecord) -> ReplyGuardVerdict | None:
    """The guard's verdict of a model reply; None for the platform's texts."""

    return None if record.model_id is None else record.guard_verdict
