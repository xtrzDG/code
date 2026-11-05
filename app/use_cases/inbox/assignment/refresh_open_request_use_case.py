from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.inbox_repositories import (
    ConversationTeamRepoContract,
    InboxWorkRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.inbox.assignment import OpenRequestRefresh, OpenRequestState
from app.schemas.typings.inbox.booleans import HasOpenRequest


class RefreshOpenRequestUseCase(UseCaseContract[OpenRequestRefresh, OpenRequestState]):
    """
    A request of a conversation was made or changed status: recount (one
    indexed count) whether any request of the conversation is new or in
    progress, and store it on the conversation, which puts it into the
    inbox's "Requests" view and makes it wait for the team, or takes it out.
    Counting instead of adding and subtracting keeps the flag right even
    after a failed write: the next change of a request repairs it.
    """

    def __init__(
        self,
        conversation_repo: ConversationTeamRepoContract,
        inbox_work_repo: InboxWorkRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._conversation_repo: ConversationTeamRepoContract = conversation_repo
        self._inbox_work_repo: InboxWorkRepoContract = inbox_work_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OpenRequestRefresh) -> OpenRequestState:
        has_open_request: HasOpenRequest = self._inbox_work_repo.has_open_request(
            input_data.business_id, input_data.conversation_id
        )
        self._conversation_repo.set_open_request(
            input_data.business_id,
            input_data.conversation_id,
            has_open_request,
            self._wall_clock.now_unix(),
        )
        return OpenRequestState(
            conversation_id=input_data.conversation_id,
            has_open_request=has_open_request,
        )
