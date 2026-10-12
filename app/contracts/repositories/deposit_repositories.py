"""
Persistence contracts of deposits: each business's settings, the deposits
asked and the bookings' outcomes the reports compare. Every read is
limited to one business, except the minute's sweeps, which look across
businesses by indexed status and time.
"""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.deposits import DepositRequestDocument, DepositSettingsDocument
from app.schemas.dto.deposits.deposit_counts import BookingOutcomeRow, DepositSumRow
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit

type DepositSettingsChange = Callable[
    [DepositSettingsDocument], DepositSettingsDocument | None
]
type DepositRequestChange = Callable[
    [DepositRequestDocument], DepositRequestDocument | None
]


class DepositSettingsRepoContract(RepoContract, Protocol):
    def get_by_business(
        self, business_id: BusinessId
    ) -> DepositSettingsDocument | None:
        """The business's settings; None: deposits were never set up (off)."""
        raise NotImplementedError

    def save(self, settings: DepositSettingsDocument) -> None:
        raise NotImplementedError

    def update(
        self, business_id: BusinessId, change: DepositSettingsChange
    ) -> DepositSettingsDocument | None:
        """
        What `change` makes of the stored settings, written in one step (a
        change made meanwhile is never overwritten); None when there are
        none yet or `change` keeps them as they are.
        """
        raise NotImplementedError


class DepositRequestRepoContract(RepoContract, Protocol):
    def save(self, request: DepositRequestDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, request_id: DepositRequestId
    ) -> DepositRequestDocument | None:
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        request_id: DepositRequestId,
        change: DepositRequestChange,
    ) -> DepositRequestDocument | None:
        """What `change` makes of the stored request, in one step (see above)."""
        raise NotImplementedError

    def list_of_booking(
        self, business_id: BusinessId, booking_id: BookingId
    ) -> list[DepositRequestDocument]:
        """The deposits asked for a booking, oldest first."""
        raise NotImplementedError

    def list_of_lead(
        self, business_id: BusinessId, lead_id: LeadId
    ) -> list[DepositRequestDocument]:
        """The deposits asked for a banquet request, oldest first."""
        raise NotImplementedError

    def list_lapsed_holds(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[DepositRequestDocument]:
        """Across businesses: deposits still AWAITING whose hold ended by `now`."""
        raise NotImplementedError

    def list_due_reminders(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[DepositRequestDocument]:
        """Across businesses: deposits still AWAITING whose reminder is due."""
        raise NotImplementedError

    def list_due_settlements(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[DepositRequestDocument]:
        """Across businesses: deposits whose settling after a cancellation is due."""
        raise NotImplementedError

    def sum_paid(
        self, business_id: BusinessId, start: Microseconds, end: Microseconds
    ) -> list[DepositSumRow]:
        """
        Deposits paid from `start` to `end` (UTC microseconds), per state and
        currency, counted and summed by the database; sandbox left out.
        """
        raise NotImplementedError

    def sum_requested(
        self, business_id: BusinessId, start: Microseconds, end: Microseconds
    ) -> list[DepositSumRow]:
        """Deposits asked from `start` to `end`, per state and currency (see above)."""
        raise NotImplementedError


class BookingOutcomeRepoContract(RepoContract, Protocol):
    def count_outcomes(
        self,
        business_id: BusinessId,
        starts_from: BookingSearchBoundSeconds,
        starts_before: BookingSearchBoundSeconds,
    ) -> list[BookingOutcomeRow]:
        """
        Bookings that started in the window (UTC seconds), per status and
        deposit state, counted by the database; sandbox left out.
        """
        raise NotImplementedError
