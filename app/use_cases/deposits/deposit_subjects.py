"""
What a deposit is asked for in a conversation: the customer's own booking
or banquet request the model names (never another customer's, never one of
another mode: a test chat's stay in the test chat), or else the latest one
made in this conversation that still waits for its visit.
"""

from dataclasses import dataclass

from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    LeadRepoContract,
)
from app.schemas.constants.bookings import LeadStatus, LeadType
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.dto.deposits.payment_link_requests import SendPaymentLinkCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.deposits.booking_deposit_state import OPEN_BOOKING_STATUSES

OPEN_LEAD_STATUSES: frozenset[LeadStatus] = frozenset(
    {LeadStatus.NEW, LeadStatus.IN_PROGRESS}
)


@dataclass(frozen=True)
class DepositSubjects:
    booking_repo: BookingRepoContract
    lead_repo: LeadRepoContract

    def find(
        self, command: SendPaymentLinkCommand
    ) -> BookingDocument | LeadDocument | None:
        """
        Raises:
            NotFoundError: the named booking or request is not this customer's.
        """

        if command.booking_id is not None:
            booking = self.booking_repo.get(command.business_id, command.booking_id)
            if booking is None or not is_own(booking, command):
                raise NotFoundError(
                    f"Booking {command.booking_id} is not one of this customer's."
                )
            return booking

        if command.lead_id is not None:
            lead = self.lead_repo.get(command.business_id, command.lead_id)
            if lead is None or not is_own(lead, command):
                raise NotFoundError(
                    f"Request {command.lead_id} is not one of this customer's."
                )
            return lead

        return self._latest_of_conversation(command)

    def _latest_of_conversation(
        self, command: SendPaymentLinkCommand
    ) -> BookingDocument | LeadDocument | None:
        if command.conversation_id is None:
            return None

        made: list[BookingDocument | LeadDocument] = [
            booking
            for booking in self.booking_repo.list_by_conversation(
                command.business_id, command.conversation_id
            )
            if is_own(booking, command) and booking.status in OPEN_BOOKING_STATUSES
        ]
        made.extend(
            lead
            for lead in self.lead_repo.list_by_conversation(
                command.business_id, command.conversation_id
            )
            if is_own(lead, command)
            and lead.lead_type is LeadType.BANQUET
            and lead.status in OPEN_LEAD_STATUSES
        )
        return max(made, key=lambda subject: int(subject.created_at), default=None)


def is_own(
    subject: BookingDocument | LeadDocument, command: SendPaymentLinkCommand
) -> bool:
    return (
        subject.contact_id == command.contact_id
        and subject.is_sandbox == command.is_sandbox
    )
