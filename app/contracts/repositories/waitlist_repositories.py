"""
Persistence contracts of the waitlist: each business's settings and the
customers' entries. Every read is limited to one business, except the
sweep's two, which look across businesses by indexed status and time:
offers whose hold ran out and entries whose day passed.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistSettingsDocument
from app.schemas.dto.growth.growth_counts import WaitlistStatusCount
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.waitlist.prefixed_id import WaitlistEntryId

type WaitlistEntryChange = Callable[
    [WaitlistEntryDocument], WaitlistEntryDocument | None
]


class WaitlistSettingsRepoContract(RepoContract, Protocol):
    def get_by_business(
        self, business_id: BusinessId
    ) -> WaitlistSettingsDocument | None:
        """The business's settings; None: the defaults (on, a 30-minute hold)."""
        raise NotImplementedError

    def save(self, settings: WaitlistSettingsDocument) -> None:
        raise NotImplementedError


class WaitlistEntryRepoContract(
    BusinessDocumentPagesContract[WaitlistEntryDocument], RepoContract, Protocol
):
    def save(self, entry: WaitlistEntryDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, entry_id: WaitlistEntryId
    ) -> WaitlistEntryDocument | None:
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        entry_id: WaitlistEntryId,
        change: WaitlistEntryChange,
    ) -> WaitlistEntryDocument | None:
        """
        Store what `change` makes of the entry as stored now, in one step
        (a row lock: a "yes" and the sweep never both win); None, and
        nothing written, when it is missing or `change` returns None.
        """
        raise NotImplementedError

    def list_of_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> list[WaitlistEntryDocument]:
        """A customer's entries, oldest first."""
        raise NotImplementedError

    def list_in_status(
        self,
        business_id: BusinessId,
        status: WaitlistStatus,
        limit: DocumentQueryLimit,
    ) -> list[WaitlistEntryDocument]:
        """Entries in one status, first come first (the queue a freed place goes to)."""
        raise NotImplementedError

    def page_in_statuses(
        self,
        business_id: BusinessId,
        statuses: Sequence[WaitlistStatus],
        window: KeysetSlice,
        is_descending: bool,
    ) -> list[WaitlistEntryDocument]:
        """One keyset page of the entries in these statuses by when they joined."""
        raise NotImplementedError

    def count_by_status(self, business_id: BusinessId) -> list[WaitlistStatusCount]:
        """How many real (not test) entries are in each status."""
        raise NotImplementedError

    def list_lapsed_offers(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[WaitlistEntryDocument]:
        """Across businesses: OFFERED entries whose hold ended by `now`."""
        raise NotImplementedError

    def list_past_waiting(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[WaitlistEntryDocument]:
        """Across businesses: WAITING entries whose day ended by `now`."""
        raise NotImplementedError
