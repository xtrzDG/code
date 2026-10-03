"""Use cases tell open cabinets what changed: one line after the write."""

import logging
import secrets
from collections.abc import Sequence

from base_typed_id import BasePrefixedTypedId
from pydantic import ValidationError
from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import (
    EventPublisherFacilitatorContract,
    LiveEventBusAdapterContract,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.live_events import MAX_LIVE_EVENT_SUBJECTS, LiveEvent
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.live_events.constrained_strings import (
    LiveEventId,
    LiveEventSubjectId,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
# 4 random bytes: two events of the same microsecond still differ.
EVENT_ID_RANDOM_BYTES: int = 4


class EventPublisherFacilitator(EventPublisherFacilitatorContract):
    """
    Builds the event (a fresh id, the time, the business, the kind and the
    ids) and publishes it on the bus. A failure is logged and swallowed:
    the change itself is stored already, and a cabinet that missed the
    event catches up at its next reload or reconnect.
    """

    def __init__(
        self,
        bus: LiveEventBusAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._bus: LiveEventBusAdapterContract = bus
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def publish(
        self,
        business_id: BusinessId,
        event: LiveEventKind,
        ids: Sequence[BasePrefixedTypedId] = (),
        is_sandbox: IsSandboxConversation = False,
    ) -> None:
        if is_sandbox:
            return

        try:
            live_event: LiveEvent = self._build(business_id, event, ids)
            self._bus.publish(live_event)
        except (ApplicationError, ValidationError) as error:
            LOGGER.warning(
                "Live event %s of business %s was not published: %s",
                event.value,
                business_id,
                type(error).__name__,
            )

    def _build(
        self,
        business_id: BusinessId,
        event: LiveEventKind,
        ids: Sequence[BasePrefixedTypedId],
    ) -> LiveEvent:
        now: Microseconds = self._wall_clock.now_unix()
        return LiveEvent(
            id=LiveEventId(
                f"{int(now):017d}-{secrets.token_hex(EVENT_ID_RANDOM_BYTES)}"
            ),
            business_id=business_id,
            event=event,
            ids=[
                LiveEventSubjectId(str(subject_id))
                for subject_id in ids[:MAX_LIVE_EVENT_SUBJECTS]
            ],
            occurred_at=now,
        )
