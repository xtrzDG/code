from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.inbound_bursts import HeldInboundEvents
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.utilities.deliveries.inbound_claims import is_inbound_event_finished


class FinishHeldInboundEventsUseCase(
    UseCaseContract[HeldInboundEvents, ProcessedItemCount]
):
    """
    Close the messages of a burst that the reply to a later message answered:
    each takes that event's outcome (ANSWERED with its outbox message and
    conversation, or HANDED_OFF when staff own the conversation), so the
    inbox shows every message as answered by the one reply. A message
    already finished (by its own reply, e.g. a STOP) is left as it is.
    How many were closed.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: HeldInboundEvents) -> ProcessedItemCount:
        answered_by: InboundEventDocument = input_data.answered_by
        now: Microseconds = self._wall_clock.now_unix()

        def finish(current: InboundEventDocument) -> InboundEventDocument | None:
            if is_inbound_event_finished(current):
                return None

            current.status = answered_by.status
            current.lease_until = None
            current.last_error = None
            current.conversation_id = answered_by.conversation_id
            current.outbound_message_id = answered_by.outbound_message_id
            current.processed_at = now
            current.updated_at = now
            return current

        closed: int = 0
        for event in input_data.events:
            if (
                self._inbound_event_repo.update(event.business_id, event.id, finish)
                is not None
            ):
                closed += 1

        return ProcessedItemCount(closed)
