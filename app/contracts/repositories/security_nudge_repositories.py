from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.security_nudges import SecurityNudgeDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.security_nudges.constrained_integers import TeamMemberCount
from app.schemas.typings.users.prefixed_id import UserId


class SecurityNudgeRepoContract(RepoContract, Protocol):
    def get(
        self, business_id: BusinessId, user_id: UserId
    ) -> SecurityNudgeDocument | None:
        raise NotImplementedError

    def dismiss(
        self,
        business_id: BusinessId,
        user_id: UserId,
        team_size: TeamMemberCount,
        now: Microseconds,
    ) -> SecurityNudgeDocument:
        """Remember that the person put the reminder away now, with this team."""
        raise NotImplementedError

    def forget(self, business_id: BusinessId, user_id: UserId) -> None:
        """Forget the person's answer in the business (their account went)."""
        raise NotImplementedError
