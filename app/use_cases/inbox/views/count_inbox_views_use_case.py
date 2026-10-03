from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.inbox_views import InboxViewCounts, InboxViewCountsQuery


class CountInboxViewsUseCase(UseCaseContract[InboxViewCountsQuery, InboxViewCounts]):
    """
    The counts of the team inbox's views as one member sees them ("mine"
    is theirs), one grouped count of the conversations waiting for the
    team. Only numbers leave this use case, so it writes no audit entry:
    the cabinet asks again after each live event of the business.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationTeamRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo

    def run(self, input_data: InboxViewCountsQuery) -> InboxViewCounts:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return self._conversation_repo.count_inbox(business.id, input_data.user_id)
