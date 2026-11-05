from app.contracts.repositories.inbox_repositories import InboxSettingsRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.inbox.inbox_settings import InboxSettingsQuery, InboxSettingsView
from app.use_cases.inbox.settings.settings_views import build_settings_view


class GetInboxSettingsUseCase(UseCaseContract[InboxSettingsQuery, InboxSettingsView]):
    """
    How the team inbox shares new work (owners and staff read it: staff
    see whether new handoffs come to them automatically).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        inbox_settings_repo: InboxSettingsRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._inbox_settings_repo: InboxSettingsRepoContract = inbox_settings_repo

    def run(self, input_data: InboxSettingsQuery) -> InboxSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return build_settings_view(
            business.id, self._inbox_settings_repo.get_by_business(business.id)
        )
