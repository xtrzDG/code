"""A business's closure, and the deletion ledger that outlives the business."""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.business_closures import (
    BusinessClosureDocument,
    BusinessDeletionDocument,
)
from app.schemas.typings.business_closures.prefixed_id import BusinessDeletionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.prefixed_id import UserId

type BusinessClosureChange = Callable[
    [BusinessClosureDocument], BusinessClosureDocument | None
]
type BusinessDeletionChange = Callable[
    [BusinessDeletionDocument], BusinessDeletionDocument | None
]


class BusinessClosureRepoContract(RepoContract, Protocol):
    """One closure per business, under the id derived from it."""

    def get(self, business_id: BusinessId) -> BusinessClosureDocument | None:
        raise NotImplementedError

    def open(self, closure: BusinessClosureDocument) -> bool:
        """
        Store a new closure in one atomic step: False, and nothing written,
        when the business already has one (two owners closing it at once).
        """
        raise NotImplementedError

    def modify(
        self, business_id: BusinessId, change: BusinessClosureChange
    ) -> BusinessClosureDocument | None:
        """
        Apply `change` to the stored closure in one step (no other write in
        between); what was written, None when it is missing or `change`
        declined.
        """
        raise NotImplementedError

    def remove(self, business_id: BusinessId) -> None:
        raise NotImplementedError

    def page_due(
        self,
        due_at: Microseconds,
        after: BusinessClosureDocument | None,
        limit: DocumentQueryLimit,
    ) -> list[BusinessClosureDocument]:
        """
        Across businesses: closures whose `delete_after` is at most `due_at`,
        soonest first, after `after` (a keyset page, so the sweep walks
        any number of them).
        """
        raise NotImplementedError


class BusinessDeletionRepoContract(RepoContract, Protocol):
    """The deletion ledger: one entry per deleted business (platform-wide)."""

    def begin(self, entry: BusinessDeletionDocument) -> bool:
        """
        Store the entry of a deletion that starts, atomically: False, and
        nothing written, when the business's deletion has an entry already.
        """
        raise NotImplementedError

    def get(self, deletion_id: BusinessDeletionId) -> BusinessDeletionDocument | None:
        raise NotImplementedError

    def find_by_business(
        self, business_id: BusinessId
    ) -> BusinessDeletionDocument | None:
        raise NotImplementedError

    def modify(
        self, deletion_id: BusinessDeletionId, change: BusinessDeletionChange
    ) -> BusinessDeletionDocument | None:
        raise NotImplementedError

    def list_of_owner(
        self, user_id: UserId, limit: DocumentQueryLimit
    ) -> list[BusinessDeletionDocument]:
        """The entries naming this person among the owners, newest first."""
        raise NotImplementedError
