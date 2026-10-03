"""
Persistence contracts of bookings, leads, handoffs and unanswered questions.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved. Every business-owned document is
looked up through its business id, so one tenant never sees another's data.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.contracts.repositories.booking_listing_contracts import (
    BookingListingContract,
    HandoffListingContract,
    LeadListingContract,
    UnansweredQuestionListingContract,
)
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId


class BookingRepoContract(BookingListingContract, RepoContract, Protocol):
    def save(self, booking: BookingDocument) -> None:
        raise NotImplementedError

    def save_many(self, bookings: Sequence[BookingDocument]) -> None:
        """Store many in one transaction: bulk loads (`workshop seed-load`)."""
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        booking_id: BookingId,
    ) -> BookingDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[BookingDocument]:
        """Return bookings ordered by starts_at ascending."""
        raise NotImplementedError


class LeadRepoContract(LeadListingContract, RepoContract, Protocol):
    def save(self, lead: LeadDocument) -> None:
        raise NotImplementedError

    def get(self, business_id: BusinessId, lead_id: LeadId) -> LeadDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[LeadDocument]:
        """Return leads ordered by created_at descending."""
        raise NotImplementedError


class HandoffRepoContract(HandoffListingContract, RepoContract, Protocol):
    def save(self, handoff: HandoffDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        handoff_id: HandoffId,
    ) -> HandoffDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[HandoffDocument]:
        """Return handoffs ordered by created_at descending."""
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        handoff_id: HandoffId,
        change: Callable[[HandoffDocument], HandoffDocument | None],
    ) -> HandoffDocument | None:
        """
        Store what `change` makes of the handoff as stored now, in one step;
        None, and nothing written, when it is missing, belongs to another
        business, or `change` returns None.
        """
        raise NotImplementedError


class UnansweredQuestionRepoContract(
    UnansweredQuestionListingContract, RepoContract, Protocol
):
    def save(self, question: UnansweredQuestionDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        question_id: UnansweredQuestionId,
    ) -> UnansweredQuestionDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[UnansweredQuestionDocument]:
        """Return questions ordered by occurrence_count descending."""
        raise NotImplementedError
