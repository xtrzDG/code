"""What waits for a person in a business: the badges of the cabinet's navigation."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.attention_repositories import (
    AttentionCountRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.operations.attention_counts import (
    AttentionCounts,
    AttentionCountsQuery,
)
from app.use_cases.bookings.operations_support import require_business


class GetAttentionCountsUseCase(UseCaseContract[AttentionCountsQuery, AttentionCounts]):
    """
    Open handoffs, new requests, pending bookings that have not started yet
    and channels in error, each one indexed count (sandbox excluded). Only
    numbers leave this use case, so it writes no audit entry: the cabinet
    asks again after each live event of the business.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        attention_count_repo: AttentionCountRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._attention_count_repo: AttentionCountRepoContract = attention_count_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AttentionCountsQuery) -> AttentionCounts:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        counts: AttentionCountRepoContract = self._attention_count_repo
        return AttentionCounts(
            business_id=business.id,
            open_handoff_count=counts.count_open_handoffs(business.id),
            new_lead_count=counts.count_new_leads(business.id),
            unconfirmed_booking_count=counts.count_unconfirmed_bookings(
                business.id, self._wall_clock.now_unix()
            ),
            channel_error_count=counts.count_failing_channels(business.id),
        )
