"""
Indexed counts of what waits for a person in a business: the badges of the
cabinet's navigation. Each count is one index lookup of the business (never
a read of its documents), so the cabinet may ask after every live event.
Sandbox activity (the owner's test chat, autotests) is never counted.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ListItemCount


class AttentionCountRepoContract(RepoContract, Protocol):
    def count_open_handoffs(self, business_id: BusinessId) -> ListItemCount:
        """Handoffs nobody has resolved yet (pending, notified or not delivered)."""
        raise NotImplementedError

    def count_new_leads(self, business_id: BusinessId) -> ListItemCount:
        """Requests still in the "new" status."""
        raise NotImplementedError

    def count_unconfirmed_bookings(
        self,
        business_id: BusinessId,
        starting_from: Microseconds,
    ) -> ListItemCount:
        """Pending bookings that start at `starting_from` or later."""
        raise NotImplementedError

    def count_failing_channels(self, business_id: BusinessId) -> ListItemCount:
        """Channels the platform refused (status ERROR)."""
        raise NotImplementedError
