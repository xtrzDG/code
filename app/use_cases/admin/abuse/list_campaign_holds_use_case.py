from app.contracts.repositories.campaign_repositories import (
    CampaignSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_campaign_holds import (
    CampaignHoldList,
    CampaignHoldView,
    ListCampaignHoldsQuery,
)
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest


class ListCampaignHoldsUseCase(
    UseCaseContract[ListCampaignHoldsQuery, CampaignHoldList]
):
    """
    The campaigns held for the platform team's review (ABUSE-05), the
    longest held first, for an admin who sees operations. Only switched-on
    campaigns write, so only they are read (the job's own indexed list).

    Raises:
        AccessDeniedError: the user is not a platform admin who sees
            operations.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        campaign_settings_repo: CampaignSettingsRepoContract,
    ) -> None:
        self._authorize: UseCaseContract[PlatformAdminAccessRequest, UserDocument] = (
            authorize_platform_admin
        )
        self._settings_repo: CampaignSettingsRepoContract = campaign_settings_repo

    def run(self, input_data: ListCampaignHoldsQuery) -> CampaignHoldList:
        self._authorize.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        holds: list[CampaignHoldView] = [
            CampaignHoldView(
                business_id=settings.business_id,
                held_at=settings.review_hold.held_at,
                sent=settings.review_hold.sent,
                opted_out=settings.review_hold.opted_out,
            )
            for settings in self._settings_repo.list_enabled()
            if settings.review_hold is not None
        ]
        return CampaignHoldList(items=sorted(holds, key=lambda hold: int(hold.held_at)))
