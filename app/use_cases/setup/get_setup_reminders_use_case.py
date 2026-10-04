from app.contracts.repositories.setup_repositories import SetupStateRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import SetupStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.setup_guide import SetupRemindersQuery, SetupRemindersView
from app.schemas.typings.setup.booleans import AreSetupRemindersOn


class GetSetupRemindersUseCase(
    UseCaseContract[SetupRemindersQuery, SetupRemindersView]
):
    """
    Whether the owners of a business get activation reminders (on until an
    owner turns them off in Settings, Notifications). Owners and staff may
    read it.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        setup_state_repo: SetupStateRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._setup_state_repo: SetupStateRepoContract = setup_state_repo

    def run(self, input_data: SetupRemindersQuery) -> SetupRemindersView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        state: SetupStateDocument | None = self._setup_state_repo.get_by_business(
            business.id
        )
        return SetupRemindersView(
            business_id=business.id,
            is_on=AreSetupRemindersOn(state is None or state.reminders_off_at is None),
        )
