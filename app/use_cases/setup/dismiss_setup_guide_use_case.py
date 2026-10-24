from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.setup_repositories import SetupStateRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.setup_guide import DismissSetupGuideCommand
from app.schemas.dto.setup.setup_progress import SetupQuery, SetupView
from app.schemas.exceptions.application_errors import ConflictError


class DismissSetupGuideUseCase(UseCaseContract[DismissSetupGuideCommand, SetupView]):
    """
    An owner puts the finished guide away (the Overview card and the
    progress ring stop showing), or brings it back. Only a finished guide
    goes away: the assistant live and every step done or skipped (an owner
    who does not want a step skips it). Returns the setup then.

    Raises:
        ConflictError: the guide is not finished yet.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        setup_state_repo: SetupStateRepoContract,
        get_setup_progress: UseCaseContract[SetupQuery, SetupView],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._setup_state_repo: SetupStateRepoContract = setup_state_repo
        self._get_setup_progress: UseCaseContract[SetupQuery, SetupView] = (
            get_setup_progress
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DismissSetupGuideCommand) -> SetupView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        query = SetupQuery(user_id=input_data.user_id, business_id=business.id)
        if (
            input_data.is_dismissed
            and not self._get_setup_progress.run(query).guide.is_complete
        ):
            raise ConflictError(
                "The setup guide is not finished yet: do or skip its steps first."
            )

        now: Microseconds = self._wall_clock.now_unix()

        def put_away(state: SetupStateDocument) -> None:
            if not input_data.is_dismissed:
                state.guide_dismissed_at = None
            elif state.guide_dismissed_at is None:
                state.guide_dismissed_at = now

        self._setup_state_repo.change(business.id, put_away, now)
        return self._get_setup_progress.run(query)
