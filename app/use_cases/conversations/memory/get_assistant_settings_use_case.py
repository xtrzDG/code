from app.contracts.repositories.customer_memory_repositories import (
    AssistantSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customer_memory.assistant_settings import (
    AssistantSettingsQuery,
    AssistantSettingsView,
)
from app.utilities.memory.assistant_settings_views import view_assistant_settings


class GetAssistantSettingsUseCase(
    UseCaseContract[AssistantSettingsQuery, AssistantSettingsView]
):
    """
    Settings → General for the team (owners and staff read, owners change):
    whether the assistant remembers returning customers and whether the
    team's notes reach that memory; the defaults while nobody changed them.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        assistant_settings_repo: AssistantSettingsRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._assistant_settings_repo: AssistantSettingsRepoContract = (
            assistant_settings_repo
        )

    def run(self, input_data: AssistantSettingsQuery) -> AssistantSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return view_assistant_settings(
            self._assistant_settings_repo.get_by_business(business.id)
        )
