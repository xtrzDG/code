from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.setup_repositories import SetupStateRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.setup_guide import StartPhoneCheckCommand
from app.schemas.dto.setup.setup_progress import SetupQuery, SetupView


class StartPhoneCheckUseCase(UseCaseContract[StartPhoneCheckCommand, SetupView]):
    """
    "Try it from your phone": the owner (or a staff member) opened the QR
    code, so for the next half hour a real conversation that starts counts
    as their message from the phone (the web chat cannot tell who writes;
    messages from the owner's own numbers and chats count at any time).
    Opening it again starts the window anew. Returns the setup then.
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

    def run(self, input_data: StartPhoneCheckCommand) -> SetupView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        now: Microseconds = self._wall_clock.now_unix()

        def listen(state: SetupStateDocument) -> None:
            if state.phone_tested_at is None:
                state.phone_check_started_at = now

        self._setup_state_repo.change(business.id, listen, now)
        return self._get_setup_progress.run(
            SetupQuery(user_id=input_data.user_id, business_id=business.id)
        )
