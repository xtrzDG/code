from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.security_nudge_repositories import (
    SecurityNudgeRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.security_nudges import (
    DismissSecurityNudgeCommand,
    SecurityNudgeSource,
    SecurityNudgeView,
)
from app.schemas.typings.security_nudges.constrained_integers import TeamMemberCount


class DismissSecurityNudgeUseCase(
    UseCaseContract[DismissSecurityNudgeCommand, SecurityNudgeView]
):
    """
    An owner puts the second-factor reminder away (the banner and the setup
    guide's step). It remembers the team's size then: put away by an owner
    working alone, the reminder comes back once the team grows past one
    person. Putting it away again is harmless. Returns the reminder then.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        describe_security_nudge: UseCaseContract[
            SecurityNudgeSource, SecurityNudgeView
        ],
        security_nudge_repo: SecurityNudgeRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize: UseCaseContract[BusinessAccessRequest, BusinessDocument] = (
            authorize_business_access
        )
        self._describe: UseCaseContract[SecurityNudgeSource, SecurityNudgeView] = (
            describe_security_nudge
        )
        self._security_nudge_repo: SecurityNudgeRepoContract = security_nudge_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DismissSecurityNudgeCommand) -> SecurityNudgeView:
        business: BusinessDocument = self._authorize.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        self._security_nudge_repo.dismiss(
            business.id,
            input_data.user_id,
            TeamMemberCount(len(business.members)),
            self._wall_clock.now_unix(),
        )
        return self._describe.run(
            SecurityNudgeSource(business=business, user_id=input_data.user_id)
        )
