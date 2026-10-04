from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.setup_repositories import SetupStateRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.setup_guide import (
    SetupRemindersView,
    UpdateSetupRemindersCommand,
)
from app.schemas.typings.setup.booleans import AreSetupRemindersOn


class UpdateSetupRemindersUseCase(
    UseCaseContract[UpdateSetupRemindersCommand, SetupRemindersView]
):
    """
    An owner turns the activation reminders of a business off (no more
    nudges by e-mail, Telegram or on devices, for every owner) or on again.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        setup_state_repo: SetupStateRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._setup_state_repo: SetupStateRepoContract = setup_state_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateSetupRemindersCommand) -> SetupRemindersView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        is_on: bool = bool(input_data.request.is_on)

        def switch(state: SetupStateDocument) -> None:
            if is_on:
                state.reminders_off_at = None
            elif state.reminders_off_at is None:
                state.reminders_off_at = now

        state: SetupStateDocument = self._setup_state_repo.change(
            business.id, switch, now
        )
        return SetupRemindersView(
            business_id=business.id,
            is_on=AreSetupRemindersOn(state.reminders_off_at is None),
        )
