from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.contact_activity_repositories import (
    ContactActivityRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerHistoryRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.contacts import ContactActivityTotals
from app.schemas.dto.customers.customer_card import (
    ContactStandingQuery,
    ContactStandingView,
)
from app.schemas.dto.customers.customer_records import ContactVisits
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.contacts.customer_standing import standing_of


class GetContactStandingUseCase(
    UseCaseContract[ContactStandingQuery, ContactStandingView]
):
    """
    The line under a conversation's customer: "Regular customer · 4
    visits", or new, returning, VIP, blocked. Owners and staff; three
    indexed reads (the contact, its counts, its visits), no personal data
    in the answer, so no audit entry.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        contact_repo: ContactRepoContract,
        contact_activity_repo: ContactActivityRepoContract,
        customer_history_repo: CustomerHistoryRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._contact_repo: ContactRepoContract = contact_repo
        self._contact_activity_repo: ContactActivityRepoContract = contact_activity_repo
        self._customer_history_repo: CustomerHistoryRepoContract = customer_history_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ContactStandingQuery) -> ContactStandingView:
        """
        Raises:
            NotFoundError: no such customer in the business.
        """

        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        contact: ContactDocument | None = self._contact_repo.get(
            business.id, input_data.contact_id
        )
        if contact is None:
            raise NotFoundError(f"Contact {input_data.contact_id} was not found.")

        totals: ContactActivityTotals = self._contact_activity_repo.count_for_contacts(
            business.id, [contact.id]
        ).get(contact.id, ContactActivityTotals())
        visits: ContactVisits = self._customer_history_repo.visits_for_contacts(
            business.id, [contact.id], self._wall_clock.now_unix()
        ).get(contact.id, ContactVisits())
        return ContactStandingView(
            contact_id=contact.id,
            standing=standing_of(visits.visit_count, totals.conversation_count),
            visit_count=visits.visit_count,
            last_visit_at=visits.last_visit_at,
            conversation_count=totals.conversation_count,
            booking_count=totals.booking_count,
            is_vip=contact.is_vip,
            is_blocked=contact.block is not None,
            is_erased=contact.erased_at is not None,
        )
