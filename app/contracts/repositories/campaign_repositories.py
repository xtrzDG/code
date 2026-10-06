"""
Persistence contracts of the rebooking campaigns: each business's settings
and the messages sent (or skipped). Every read is limited to one business,
except the campaign job's look for the businesses that turned it on.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.campaigns import (
    CampaignMessageDocument,
    CampaignSettingsDocument,
)
from app.schemas.dto.growth.growth_counts import CampaignStatusCount, OriginBookingCount
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.campaigns.constrained_integers import CampaignMessageCount
from app.schemas.typings.campaigns.constrained_strings import CampaignMonthKey
from app.schemas.typings.campaigns.prefixed_id import CampaignMessageId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.booleans import IsDocumentInserted

type CampaignMessageChange = Callable[
    [CampaignMessageDocument], CampaignMessageDocument | None
]


class CampaignSettingsRepoContract(RepoContract, Protocol):
    def get_by_business(
        self, business_id: BusinessId
    ) -> CampaignSettingsDocument | None:
        """The business's settings; None: never set (off, the niche's rule)."""
        raise NotImplementedError

    def save(self, settings: CampaignSettingsDocument) -> None:
        raise NotImplementedError

    def list_enabled(self) -> list[CampaignSettingsDocument]:
        """Across businesses: the settings of every business whose campaign is on."""
        raise NotImplementedError


class CampaignMessageRepoContract(RepoContract, Protocol):
    def insert_if_new(self, message: CampaignMessageDocument) -> IsDocumentInserted:
        """Store the message unless one with its id exists (atomic)."""
        raise NotImplementedError

    def get_many(
        self, business_id: BusinessId, message_ids: Sequence[CampaignMessageId]
    ) -> dict[CampaignMessageId, CampaignMessageDocument]:
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        message_id: CampaignMessageId,
        change: CampaignMessageChange,
    ) -> CampaignMessageDocument | None:
        raise NotImplementedError

    def list_of_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> list[CampaignMessageDocument]:
        """A customer's messages (a handful), oldest first."""
        raise NotImplementedError

    def count_sent_in_month(
        self, business_id: BusinessId, month: CampaignMonthKey
    ) -> CampaignMessageCount:
        """The month's messages that went out (SENT or since BOOKED): the cap's count."""
        raise NotImplementedError

    def list_awaiting_booking(
        self, business_id: BusinessId, sent_from: Microseconds
    ) -> list[CampaignMessageDocument]:
        """SENT messages sent from `sent_from` on that no booking followed yet."""
        raise NotImplementedError

    def page_latest(
        self, business_id: BusinessId, window: KeysetSlice
    ) -> list[CampaignMessageDocument]:
        """One keyset page of the business's messages, newest first."""
        raise NotImplementedError

    def count_by_status(
        self, business_id: BusinessId, created_from: Microseconds
    ) -> list[CampaignStatusCount]:
        """How many messages of the period from `created_from` are in each status."""
        raise NotImplementedError


class OriginBookingCountRepoContract(RepoContract, Protocol):
    def count_by_origin(
        self, business_id: BusinessId, start: Microseconds, end: Microseconds
    ) -> list[OriginBookingCount]:
        """
        The waitlist's and the campaigns' bookings made from `start` to
        `end` (UTC microseconds), per origin, status and currency with their
        summed values; sandbox left out (counted by the database).
        """
        raise NotImplementedError
