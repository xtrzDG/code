"""A live event publisher for tests: it keeps what the use cases announce."""

from collections.abc import Sequence
from dataclasses import dataclass

from base_typed_id import BasePrefixedTypedId

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.booleans import IsSandboxConversation


@dataclass(frozen=True)
class PublishedLiveEvent:
    business_id: BusinessId
    event: LiveEventKind
    ids: tuple[str, ...]


class RecordingEventPublisher(EventPublisherFacilitatorContract):
    """
    Records every announced change (sandbox ones are dropped, as in the app)
    and hands it on to `forward_to` when a test sets a real publisher there.
    """

    def __init__(self) -> None:
        self.events: list[PublishedLiveEvent] = []
        self.forward_to: EventPublisherFacilitatorContract | None = None

    def publish(
        self,
        business_id: BusinessId,
        event: LiveEventKind,
        ids: Sequence[BasePrefixedTypedId] = (),
        is_sandbox: IsSandboxConversation = False,
    ) -> None:
        if is_sandbox:
            return

        self.events.append(
            PublishedLiveEvent(business_id, event, tuple(str(item) for item in ids))
        )
        if self.forward_to is not None:
            self.forward_to.publish(business_id, event, ids)

    def kinds(self) -> list[LiveEventKind]:
        return [published.event for published in self.events]
