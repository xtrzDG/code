"""A product-event facilitator for tests: keeps what the use cases report."""

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.schemas.constants.analytics import ProductEventName
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft


class RecordingProductEvents(RecordProductEventFacilitatorContract):
    """Every reported step, in order, for assertions."""

    def __init__(self) -> None:
        self.events: list[ProductEventDraft] = []

    def record(self, *events: ProductEventDraft) -> None:
        self.events.extend(events)

    def names(self) -> list[ProductEventName]:
        return [event.name for event in self.events]

    def named(self, name: ProductEventName) -> list[ProductEventDraft]:
        return [event for event in self.events if event.name is name]
