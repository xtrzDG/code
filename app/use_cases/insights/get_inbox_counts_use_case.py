"""How much waits in a business's inbox, for the badges of the cabinet's navigation."""

from app.contracts.repositories.booking_repositories import (
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import LeadStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.operations.inbox_counts import InboxCounts, InboxCountsQuery
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.use_cases.bookings.operations_support import require_business


class GetInboxCountsUseCase(UseCaseContract[InboxCountsQuery, InboxCounts]):
    """
    Open handoffs (any status but resolved) and leads still in the "new"
    status, without sandbox activity. Only numbers leave this use case, so
    it writes no audit entry: the cabinet reads it every minute for the
    badges on Messages, where a list of handoffs or leads would record a
    view of personal data nobody opened.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        handoff_repo: HandoffRepoContract,
        lead_repo: LeadRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._lead_repo: LeadRepoContract = lead_repo

    def run(self, input_data: InboxCountsQuery) -> InboxCounts:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        open_handoffs: int = sum(
            1
            for handoff in self._handoff_repo.list_by_business(business.id)
            if handoff.status is not HandoffStatus.RESOLVED and not handoff.is_sandbox
        )
        new_leads: int = sum(
            1
            for lead in self._lead_repo.list_by_business(business.id)
            if lead.status is LeadStatus.NEW and not lead.is_sandbox
        )
        return InboxCounts(
            business_id=business.id,
            open_handoff_count=ListItemCount(open_handoffs),
            new_lead_count=ListItemCount(new_leads),
        )
