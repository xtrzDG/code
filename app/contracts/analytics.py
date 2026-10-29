"""The use cases' one line into the founder's product analytics."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft


class RecordProductEventFacilitatorContract(FacilitatorContract, Protocol):
    def record(self, *events: ProductEventDraft) -> None:
        """
        Store the product events the step produced (none is fine). A
        once-only step gets the id derived from its subject, so recording it
        again changes nothing. Never raises: analytics must not fail the
        owner's action; a lost once-only step comes back with the daily
        reconciliation.
        """
        raise NotImplementedError
