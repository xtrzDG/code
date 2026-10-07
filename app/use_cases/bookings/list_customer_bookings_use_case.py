from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.customer_bookings import CustomerBookingList, CustomerBookingsQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.shared.customer_bookings import find_customer_bookings
from app.utilities.scheduling.zoned_time import microseconds_to_seconds

# Still to come, and the ones the business cancelled ("is it still on?").
LISTED_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CANCELLED}
)
MAX_LISTED_BOOKINGS: DocumentQueryLimit = DocumentQueryLimit(10)


class ListCustomerBookingsUseCase(
    UseCaseContract[CustomerBookingsQuery, CustomerBookingList]
):
    """
    The customer's own bookings that have not ended yet (model tool
    list_my_bookings, in chat and on the phone), found like cancel_booking
    finds them: by the conversation's contact and by the phone the channel
    proved (the contacts of the business under that number), never by a
    number the customer types, and only in the conversation's sandbox mode,
    so an owner test never shows a real booking. At most ten, the soonest
    first; cancelled ones are listed with their status.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        contact_repo: ContactRepoContract,
        booking_repo: BookingRepoContract,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CustomerBookingsQuery) -> CustomerBookingList:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        return CustomerBookingList(
            bookings=find_customer_bookings(
                self._booking_repo,
                self._resource_repo,
                self._knowledge_item_repo,
                business,
                self._customer_contact_ids(input_data),
                LISTED_STATUSES,
                is_sandbox=input_data.is_sandbox,
                ends_after=BookingSearchBoundSeconds(
                    microseconds_to_seconds(int(self._wall_clock.now_unix()))
                ),
                limit=MAX_LISTED_BOOKINGS,
            )
        )

    def _customer_contact_ids(self, query: CustomerBookingsQuery) -> set[ContactId]:
        """The conversation's contact and the contacts under the proved phone."""

        contact_ids: set[ContactId] = {query.contact_id}
        if query.verified_phone_number is None:
            return contact_ids

        for found in (
            self._contact_repo.find_by_verified_phone_number(
                query.business_id, query.verified_phone_number
            ),
            self._contact_repo.find_by_phone_number(
                query.business_id, query.verified_phone_number
            ),
        ):
            if found is not None and not is_erased(found):
                contact_ids.add(found.id)

        return contact_ids


def is_erased(contact: ContactDocument) -> bool:
    return contact.erased_at is not None
