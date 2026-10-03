from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.inbox_views import (
    InboxAssigneeList,
    InboxAssigneesQuery,
    InboxAssigneeView,
)
from app.schemas.typings.inbox.constrained_integers import AwaitingConversationCount


class ListInboxAssigneesUseCase(
    UseCaseContract[InboxAssigneesQuery, InboxAssigneeList]
):
    """
    The members a conversation can be assigned to, for the assign menu of
    every member (staff included): name, role and how many conversations
    waiting for the team each has now. No phone or e-mail: staff need
    names to pass work on, not their colleagues' contacts. Owners come
    first, then everyone by name.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationTeamRepoContract,
        user_repo: UserRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo
        self._user_repo: UserRepoContract = user_repo

    def run(self, input_data: InboxAssigneesQuery) -> InboxAssigneeList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        loads = self._conversation_repo.count_awaiting_by_assignee(business.id)
        assignees: list[InboxAssigneeView] = []
        for member in business.members:
            user: UserDocument | None = self._user_repo.get(member.user_id)
            assignees.append(
                InboxAssigneeView(
                    user_id=member.user_id,
                    display_name=None if user is None else user.display_name,
                    role=member.role,
                    awaiting_count=loads.get(
                        member.user_id, AwaitingConversationCount(0)
                    ),
                )
            )

        assignees.sort(
            key=lambda assignee: (
                assignee.role is not BusinessMemberRole.OWNER,
                "" if assignee.display_name is None else str(assignee.display_name),
            )
        )
        return InboxAssigneeList(items=assignees)
