"""Declined payments counted per business (card testing, LOG-05)."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.typings.businesses.prefixed_id import BusinessId


class PaymentDeclineWatchFacilitatorContract(FacilitatorContract, Protocol):
    """
    The declined payments of each business in shared hourly windows (every
    process counts in the same buckets): a burst is the platform alert
    `tenant_payment_declines`, and past the brake the business opens no new
    payment page until the windows cool down.
    """

    def record_decline(self, business_id: BusinessId) -> None:
        """Count one declined payment of the business. Never raises."""
        raise NotImplementedError

    def require_payment_pages(self, business_id: BusinessId) -> None:
        """
        Raises:
            RateLimitedError: the business's declines of the last one to two
                hours reached the brake; a new payment page may open later
                (`retry_after_seconds`).
        """
        raise NotImplementedError
