"""How much waits in a business's inbox, for the badges of the cabinet's navigation."""

from app.contracts.repositories.attention_repositories import (
    AttentionCountRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.operations.inbox_counts import InboxCounts, InboxCountsQuery
from app.use_cases.bookings.operations_support import require_business


class GetInboxCountsUseCase(UseCaseContract[InboxCountsQuery, InboxCounts]):
    """
    Open handoffs (any status but resolved) and leads still in the "new"
    status, without sandbox activity: two of the attention counts
    (`GetAttentionCountsUseCase`, which the cabinet reads now), each one
    indexed count. Only numbers leave this use case, so it writes no audit
    entry.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        attention_count_repo: AttentionCountRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._attention_count_repo: AttentionCountRepoContract = attention_count_repo

    def run(self, input_data: InboxCountsQuery) -> InboxCounts:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        return InboxCounts(
            business_id=business.id,
            open_handoff_count=self._attention_count_repo.count_open_handoffs(
                business.id
            ),
            new_lead_count=self._attention_count_repo.count_new_leads(business.id),
        )
