"""Live events and subscribers for the tests of the live stream."""

import itertools
from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.live_events import LiveEvent
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.live_events.constrained_strings import (
    LiveEventId,
    LiveEventSubjectId,
)

START_MICROSECONDS: int = 1_790_812_800_000_000
_sequence = itertools.count(1)


def event_id_at(microseconds: int, suffix: str = "00000000") -> LiveEventId:
    return LiveEventId(f"{microseconds:017d}-{suffix}")


def make_event(
    business_id: BusinessId,
    kind: LiveEventKind = LiveEventKind.BOOKING_CREATED,
    subject: str | None = None,
) -> LiveEvent:
    """A unique event of the business (ids and times grow with each call)."""

    number: int = next(_sequence)
    occurred_at: int = START_MICROSECONDS + number
    return LiveEvent(
        id=event_id_at(occurred_at, f"{number:08x}"),
        business_id=business_id,
        event=kind,
        ids=[] if subject is None else [LiveEventSubjectId(subject)],
        occurred_at=Microseconds(occurred_at),
    )


@dataclass
class RecordingSubscriber:
    """A stream that keeps what the bus hands it."""

    events: list[LiveEvent] = field(default_factory=list[LiveEvent])
    resyncs: int = 0
    ended: int = 0

    def deliver(self, event: LiveEvent) -> None:
        self.events.append(event)

    def resync(self) -> None:
        self.resyncs += 1

    def end(self) -> None:
        self.ended += 1


class BrokenSubscriber(RecordingSubscriber):
    """A stream whose connection broke: every hand-over fails."""

    def deliver(self, event: LiveEvent) -> None:
        raise RuntimeError("the stream is gone")

    def resync(self) -> None:
        raise RuntimeError("the stream is gone")

    def end(self) -> None:
        raise RuntimeError("the stream is gone")
