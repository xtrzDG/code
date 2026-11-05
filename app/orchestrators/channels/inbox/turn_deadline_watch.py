import logging
import threading
from collections.abc import Generator
from contextlib import contextmanager

from typed_time_provider import Microseconds, WallClock

from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.conversations.constrained_integers import (
    ChatTurnDeadlineSeconds,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.utilities.observability.log_context import bound_log_context

logger: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: float = 1_000_000.0
# A holding reply still being queued when the turn ends is waited for, so it
# is in the outbox before the answer.
JOIN_SECONDS: float = 5.0


class TurnDeadlineWatch:
    """
    The turn deadline of a customer's messages: when the reply is still
    being written CHAT_TURN_DEADLINE_SECONDS after the customer's first
    unanswered message, `send_holding_reply` runs once from a timer thread
    of its own (in the business's storage scope); then comes the answer or
    a handoff. A turn that ends earlier cancels the timer, and leaving the
    watch waits for a holding reply already on its way, so the customer
    gets it before the answer. Failures are logged, never raised.
    """

    def __init__(
        self,
        send_holding_reply: UseCaseContract[InboundEventDocument, MessageId | None],
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
        deadline_seconds: ChatTurnDeadlineSeconds,
    ) -> None:
        self._send_holding_reply: UseCaseContract[
            InboundEventDocument, MessageId | None
        ] = send_holding_reply
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._deadline_seconds: ChatTurnDeadlineSeconds = deadline_seconds

    @contextmanager
    def watch(
        self, event: InboundEventDocument, waiting_since: Microseconds
    ) -> Generator[None]:
        """Watch the turn that answers `event` (the burst's last message)."""

        if event.business_id is None or event.customer_message is None:
            yield
            return

        seconds_left: float = (
            int(waiting_since)
            + int(self._deadline_seconds) * MICROSECONDS_PER_SECOND
            - int(self._wall_clock.now_unix())
        ) / MICROSECONDS_PER_SECOND
        timer = threading.Timer(max(0.0, seconds_left), self._hold, args=(event,))
        timer.name = "turn-deadline"
        timer.daemon = True
        timer.start()
        try:
            yield
        finally:
            timer.cancel()
            timer.join(timeout=JOIN_SECONDS)

    def _hold(self, event: InboundEventDocument) -> None:
        if event.business_id is None:
            return

        try:
            with (
                bound_log_context(business_id=event.business_id, channel=event.channel),
                self._storage_scope.scoped_to_business(event.business_id),
            ):
                sent: MessageId | None = self._send_holding_reply.run(event)
        except Exception:
            logger.exception("The holding reply of event %s failed.", event.id)
            return

        if sent is not None:
            logger.info(
                "Turn deadline passed: holding reply %s sent for event %s.",
                sent,
                event.id,
            )
