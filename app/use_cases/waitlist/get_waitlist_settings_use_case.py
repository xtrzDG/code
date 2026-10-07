from app.contracts.repositories.waitlist_repositories import (
    WaitlistEntryRepoContract,
    WaitlistSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.growth.waitlist_views import (
    WaitlistSettingsQuery,
    WaitlistSettingsView,
)
from app.use_cases.waitlist.waitlist_entry_views import (
    build_settings_view,
    stored_or_default,
)


class GetWaitlistSettingsUseCase(
    UseCaseContract[WaitlistSettingsQuery, WaitlistSettingsView]
):
    """
    The waitlist's settings (on, a 30-minute hold until the owner changes
    them) and how many real entries are in each status. Owners and staff.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        waitlist_settings_repo: WaitlistSettingsRepoContract,
        waitlist_entry_repo: WaitlistEntryRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._settings_repo: WaitlistSettingsRepoContract = waitlist_settings_repo
        self._entry_repo: WaitlistEntryRepoContract = waitlist_entry_repo

    def run(self, input_data: WaitlistSettingsQuery) -> WaitlistSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return build_settings_view(
            stored_or_default(
                self._settings_repo.get_by_business(business.id),
                business.id,
                business.created_at,
            ),
            self._entry_repo.count_by_status(business.id),
        )
