from typed_time_provider import Microseconds

from app.contracts.repositories.security_nudge_repositories import (
    SecurityNudgeRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.security_nudges import SecurityNudgeDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.security_nudges.constrained_integers import TeamMemberCount
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.security_nudge_identity import security_nudge_id_for


class SecurityNudgeRepository(
    BusinessScopedRepository[SecurityNudgeDocument],
    SecurityNudgeRepoContract,
):
    """One answer per business and person, under the id derived from both."""

    def get(
        self, business_id: BusinessId, user_id: UserId
    ) -> SecurityNudgeDocument | None:
        return self._load(business_id, str(security_nudge_id_for(business_id, user_id)))

    def dismiss(
        self,
        business_id: BusinessId,
        user_id: UserId,
        team_size: TeamMemberCount,
        now: Microseconds,
    ) -> SecurityNudgeDocument:
        nudge_id = security_nudge_id_for(business_id, user_id)
        stored: SecurityNudgeDocument | None = self._load(business_id, str(nudge_id))
        nudge = SecurityNudgeDocument(
            id=nudge_id,
            business_id=business_id,
            user_id=user_id,
            dismissed_at=now,
            team_size_at_dismissal=team_size,
            created_at=now if stored is None else stored.created_at,
            updated_at=now,
        )
        self._store(str(nudge_id), nudge)
        return nudge
