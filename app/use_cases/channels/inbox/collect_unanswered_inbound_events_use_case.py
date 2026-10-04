from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffSummaryCode,
    HandoffUrgency,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.dto.handoffs import CodedHandoffSummary, HandoffCommand
from app.schemas.dto.inbox_sweep import UnansweredInboundEvent
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.strings import HandoffQuotedText
from app.use_cases.channels.inbox.inbox_sweep_rules import (
    UNANSWERED_AFTER_SECONDS,
    UNANSWERED_LOOKBACK_SECONDS,
    read_stale_events,
    seconds_before,
)

MAX_QUOTED_MESSAGE_LENGTH: int = 300


class CollectUnansweredInboundEventsUseCase(
    UseCaseContract[JobTick, list[UnansweredInboundEvent]]
):
    """
    Customer messages the assistant gave up on (FAILED: the retries ran
    out, or the business could not answer) an hour ago or more, at most a
    day before that, that no person was asked about: each becomes a
    handoff of the customer's conversation, quoting the message, so a
    person answers it. A message whose conversation staff own already, or
    that has no conversation (the business never went live), is only
    marked (no handoff to make).
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        business_repo: BusinessRepoContract,
        conversation_repo: ConversationRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> list[UnansweredInboundEvent]:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        answered_before: Microseconds = seconds_before(now, UNANSWERED_AFTER_SECONDS)
        unanswered: list[UnansweredInboundEvent] = []
        for event in read_stale_events(
            self._inbound_event_repo,
            InboundEventStatus.FAILED,
            answered_before,
            created_from=seconds_before(answered_before, UNANSWERED_LOOKBACK_SECONDS),
        ):
            if (
                event.kind is not InboundEventKind.CUSTOMER_MESSAGE
                or event.business_id is None
                or event.customer_message is None
                or event.handoff_requested_at is not None
            ):
                continue

            unanswered.append(
                UnansweredInboundEvent(
                    event_id=event.id,
                    business_id=event.business_id,
                    handoff=self._handoff(
                        event, event.business_id, event.customer_message
                    ),
                )
            )

        return unanswered

    def _handoff(
        self,
        event: InboundEventDocument,
        business_id: BusinessId,
        message: InboundCustomerMessage,
    ) -> HandoffCommand | None:
        conversation: ConversationDocument | None = self._conversation(
            event, business_id, message
        )
        business: BusinessDocument | None = self._business_repo.get(business_id)
        if (
            conversation is None
            or business is None
            or conversation.is_sandbox
            or conversation.status is ConversationStatus.HANDOFF
        ):
            return None

        return HandoffCommand(
            business_id=business_id,
            conversation_id=conversation.id,
            contact_id=conversation.contact_id,
            reason=HandoffReason.NON_STANDARD_REQUEST,
            summary=CodedHandoffSummary(
                code=HandoffSummaryCode.MODEL_UNAVAILABLE,
                quoted_text=HandoffQuotedText(
                    str(message.text)[:MAX_QUOTED_MESSAGE_LENGTH] or "…"
                ),
            ),
            urgency=HandoffUrgency.HIGH,
            source_channel=conversation.channel,
            language=conversation.language or business.default_language,
        )

    def _conversation(
        self,
        event: InboundEventDocument,
        business_id: BusinessId,
        message: InboundCustomerMessage,
    ) -> ConversationDocument | None:
        """The event's conversation, else the customer's latest in the channel."""

        if event.conversation_id is not None:
            return self._conversation_repo.get(business_id, event.conversation_id)

        latest: list[ConversationDocument] = (
            self._conversation_repo.list_by_channel_user(
                business_id, event.channel, message.channel_user_id
            )
        )
        return next(
            (conversation for conversation in latest if not conversation.is_sandbox),
            None,
        )
