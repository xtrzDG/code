"""In-memory analytics storage and a fixed clock for the analytics tests."""

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.analytics_repositories import (
    ProductEventRepository,
    WebVitalSampleRepository,
)
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.web_vitals import WebVitalSampleDocument

NANOSECONDS_PER_MICROSECOND: int = 1_000
# 2026-09-21T12:26:40Z.
START_MICROSECONDS: int = 1_790_000_000_000_000


class SettableClock:
    """A wall clock the test moves by hand."""

    def __init__(self, microseconds: int = START_MICROSECONDS) -> None:
        self.microseconds: int = microseconds

    def wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: (
                self.microseconds * NANOSECONDS_PER_MICROSECOND
            ),
        )

    def now(self) -> Microseconds:
        return Microseconds(self.microseconds)


def product_event_repo() -> ProductEventRepository:
    return ProductEventRepository(
        InMemoryDocumentCollectionAdapter(ProductEventDocument)
    )


def web_vital_sample_repo() -> WebVitalSampleRepository:
    return WebVitalSampleRepository(
        InMemoryDocumentCollectionAdapter(WebVitalSampleDocument)
    )
