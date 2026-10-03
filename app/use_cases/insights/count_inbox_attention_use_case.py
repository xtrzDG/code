"""What waits for the team: one count for the inbox tabs and every badge."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.attention_repositories import (
    AttentionCountRepoContract,
)
from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.inbox_attention import (
    InboxAttentionCounts,
    InboxAttentionQuery,
)
from app.schemas.dto.inbox.inbox_views import InboxViewCounts
from app.schemas.typings.platform.constrained_integers import ListItemCount


class CountInboxAttentionUseCase(
    UseCaseContract[InboxAttentionQuery, InboxAttentionCounts]
):
    """
    The one place that counts what waits for a person, for GET
    …/inbox/counts and GET …/attention-counts alike: the inbox views as the
    member sees them ("mine" is theirs), in conversations, from one grouped
    count; pending bookings that have not started yet and channels in
    error, each one indexed count. Sandbox activity is left out. Only
    numbers leave this use case, so it writes no audit entry: the cabinet
    asks again after each live event of the business.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationTeamRepoContract,
        attention_count_repo: AttentionCountRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo
        self._attention_count_repo: AttentionCountRepoContract = attention_count_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: InboxAttentionQuery) -> InboxAttentionCounts:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        views: InboxViewCounts = self._conversation_repo.count_inbox(
            business.id, input_data.user_id
        )
        unconfirmed: ListItemCount = (
            self._attention_count_repo.count_unconfirmed_bookings(
                business.id, self._wall_clock.now_unix()
            )
        )
        failing: ListItemCount = self._attention_count_repo.count_failing_channels(
            business.id
        )
        return InboxAttentionCounts(
            business_id=business.id,
            needs_person=views.needs_person,
            requests=views.requests,
            unassigned=views.unassigned,
            mine=views.mine,
            unconfirmed_bookings=unconfirmed,
            channel_errors=failing,
            open_handoff_count=views.needs_person,
            new_lead_count=views.requests,
            unconfirmed_booking_count=unconfirmed,
            channel_error_count=failing,
        )
