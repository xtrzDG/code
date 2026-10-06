from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.campaign_repositories import (
    CampaignSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.growth.campaign_views import (
    CampaignSettingsQuery,
    CampaignSettingsView,
)
from app.use_cases.campaigns.campaign_settings_views import (
    CampaignSettingsReader,
    stored_or_niche_default,
)


class GetCampaignSettingsUseCase(
    UseCaseContract[CampaignSettingsQuery, CampaignSettingsView]
):
    """
    Bookings → Return visits: the campaign's settings (the niche's rule,
    off, until the owner changes them), this month's messages against the
    cap, the last 30 days by status and the message in each language of
    the business. Any member of the business.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        campaign_settings_repo: CampaignSettingsRepoContract,
        reader: CampaignSettingsReader,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._settings_repo: CampaignSettingsRepoContract = campaign_settings_repo
        self._reader: CampaignSettingsReader = reader
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CampaignSettingsQuery) -> CampaignSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        settings = stored_or_niche_default(
            self._settings_repo.get_by_business(business.id),
            business,
            self._reader.niche_rule(business),
            now,
        )
        return self._reader.view(business, settings, now)
