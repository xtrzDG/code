"""Use cases report the steps of an owner's way to paying: one line each."""

import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.repositories.analytics_repositories import (
    ProductEventRepoContract,
)
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft
from app.utilities.analytics.product_event_keys import derive_product_event_id

LOGGER: logging.Logger = logging.getLogger(__name__)


class RecordProductEventFacilitator(RecordProductEventFacilitatorContract):
    """
    Gives each reported step its id (derived for a once-only step, so a
    repeat changes nothing) and its time (now, unless the step happened
    earlier) and stores it.

    A failed write is logged and swallowed, whatever the storage raised:
    the owner's action itself is stored already and must not fail because
    of analytics; a lost once-only step is restored by the daily
    reconciliation, which derives it from the stored records.
    """

    def __init__(
        self,
        product_event_repo: ProductEventRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._product_event_repo: ProductEventRepoContract = product_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def record(self, *events: ProductEventDraft) -> None:
        for draft in events:
            try:
                self._product_event_repo.record(self._document(draft))
            except Exception:  # analytics never fail the owner's action
                LOGGER.warning(
                    "Product event %s was not recorded.",
                    draft.name.value,
                    exc_info=True,
                )

    def _document(self, draft: ProductEventDraft) -> ProductEventDocument:
        now: Microseconds = self._wall_clock.now_unix()
        return ProductEventDocument(
            id=derive_product_event_id(draft),
            name=draft.name,
            occurred_at=draft.occurred_at or now,
            source=draft.source,
            user_id=draft.user_id,
            business_id=draft.business_id,
            properties=draft.properties,
            created_at=now,
            updated_at=now,
        )
