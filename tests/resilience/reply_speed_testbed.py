"""
The worker's `process_inbound_message` orchestrator over the channels
testbed: bursts (MESSAGE_COALESCE_SECONDS), typing and the turn deadline.

The channels tests answer every message on its own (coalescing off), show
no typing and send no holding reply; the reply-speed tests pass their own.
"""

from contextlib import AbstractContextManager, nullcontext

from app.contracts.typing_signals import TypingSignalFacilitatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.channels.inbox.customer_wait import CustomerWait
from app.orchestrators.channels.inbox.inbound_burst_answers import (
    InboundBurstAnswers,
)
from app.orchestrators.channels.inbox.process_inbound_message_orchestrator import (
    ProcessInboundMessageOrchestrator,
)
from app.orchestrators.channels.inbox.turn_deadline_watch import TurnDeadlineWatch
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.channels.typing_signals import TypingRequest
from app.schemas.typings.conversations.constrained_integers import (
    ChatTurnDeadlineSeconds,
    MessageCoalesceSeconds,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.use_cases.channels.inbox.claim_inbound_burst_use_case import (
    ClaimInboundBurstUseCase,
)
from app.use_cases.channels.inbox.finish_held_inbound_events_use_case import (
    FinishHeldInboundEventsUseCase,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.channels.channels_media import ChannelsMedia

NO_COALESCING: MessageCoalesceSeconds = MessageCoalesceSeconds(0)


class RecordingTypingSignals(TypingSignalFacilitatorContract):
    """Who was shown "typing…": once, or for the whole of a turn."""

    def __init__(self) -> None:
        self.once: list[TypingRequest] = []
        self.kept: list[TypingRequest] = []

    def signal_once(self, request: TypingRequest) -> None:
        self.once.append(request)

    def keep_typing(self, request: TypingRequest) -> AbstractContextManager[None]:
        self.kept.append(request)
        return nullcontext()


class NoHoldingReply(UseCaseContract[InboundEventDocument, MessageId | None]):
    def run(self, input_data: InboundEventDocument) -> MessageId | None:
        del input_data
        return None


def process_inbound_message_orchestrator(
    testbed: ChannelsMedia,
    coalesce_seconds: MessageCoalesceSeconds = NO_COALESCING,
    typing_signals: TypingSignalFacilitatorContract | None = None,
    send_holding_reply: (
        UseCaseContract[InboundEventDocument, MessageId | None] | None
    ) = None,
    deadline_seconds: ChatTurnDeadlineSeconds | None = None,
) -> ProcessInboundMessageOrchestrator:
    return ProcessInboundMessageOrchestrator(
        claim_inbound_burst=ClaimInboundBurstUseCase(
            testbed.inbound_event_repo,
            testbed.job_queue,
            testbed.wall_clock,
            coalesce_seconds,
        ),
        answers=InboundBurstAnswers(
            testbed.recall_inbound_reply,
            testbed.pipeline,
            testbed.read_inbound_attachments,
        ),
        finish_inbound_event=testbed.finish_inbound_event,
        finish_held_inbound_events=FinishHeldInboundEventsUseCase(
            testbed.inbound_event_repo, testbed.wall_clock
        ),
        release_inbound_event=testbed.release_inbound_event,
        customer_wait=CustomerWait(
            typing_signals or RecordingTypingSignals(),
            TurnDeadlineWatch(
                send_holding_reply or NoHoldingReply(),
                StorageScopeContext(),
                testbed.wall_clock,
                deadline_seconds
                or testbed.settings.reply_speed.chat_turn_deadline_seconds,
            ),
            testbed.live_events,
        ),
    )
