from app.contracts.repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
    UnansweredQuestionRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId


class BookingRepository(
    BusinessScopedRepository[BookingDocument],
    BookingRepoContract,
):
    def save(self, booking: BookingDocument) -> None:
        self._store(str(booking.id), booking)

    def get(
        self,
        business_id: BusinessId,
        booking_id: BookingId,
    ) -> BookingDocument | None:
        return self._load(business_id, str(booking_id))

    def list_by_business(self, business_id: BusinessId) -> list[BookingDocument]:
        return sorted(self._list(business_id), key=lambda booking: booking.starts_at)


class LeadRepository(BusinessScopedRepository[LeadDocument], LeadRepoContract):
    def save(self, lead: LeadDocument) -> None:
        self._store(str(lead.id), lead)

    def get(self, business_id: BusinessId, lead_id: LeadId) -> LeadDocument | None:
        return self._load(business_id, str(lead_id))

    def list_by_business(self, business_id: BusinessId) -> list[LeadDocument]:
        return sorted(
            self._list(business_id),
            key=lambda lead: lead.created_at,
            reverse=True,
        )


class HandoffRepository(
    BusinessScopedRepository[HandoffDocument],
    HandoffRepoContract,
):
    def save(self, handoff: HandoffDocument) -> None:
        self._store(str(handoff.id), handoff)

    def get(
        self,
        business_id: BusinessId,
        handoff_id: HandoffId,
    ) -> HandoffDocument | None:
        return self._load(business_id, str(handoff_id))

    def list_by_business(self, business_id: BusinessId) -> list[HandoffDocument]:
        return sorted(
            self._list(business_id),
            key=lambda handoff: handoff.created_at,
            reverse=True,
        )


class UnansweredQuestionRepository(
    BusinessScopedRepository[UnansweredQuestionDocument],
    UnansweredQuestionRepoContract,
):
    def save(self, question: UnansweredQuestionDocument) -> None:
        self._store(str(question.id), question)

    def get(
        self,
        business_id: BusinessId,
        question_id: UnansweredQuestionId,
    ) -> UnansweredQuestionDocument | None:
        return self._load(business_id, str(question_id))

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[UnansweredQuestionDocument]:
        return sorted(
            self._list(business_id),
            key=lambda question: question.occurrence_count,
            reverse=True,
        )
