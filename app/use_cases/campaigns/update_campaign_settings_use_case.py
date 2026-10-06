from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.campaign_repositories import (
    CampaignSettingsRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.campaigns import CampaignAudience
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.growth.campaign_views import (
    CampaignSettingsRequest,
    CampaignSettingsView,
    UpdateCampaignSettingsCommand,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.campaigns.campaign_settings_views import (
    CampaignSettingsReader,
    stored_or_niche_default,
)
from app.use_cases.shared.operations_support import build_audit_entry

CAMPAIGN_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("campaign_settings")


class UpdateCampaignSettingsUseCase(
    UseCaseContract[UpdateCampaignSettingsCommand, CampaignSettingsView]
):
    """
    The owner opts the business in to its rebooking campaign (or out), and
    sets the rule, its days, who it may write to (everyone the rule finds,
    or the members of one saved segment of this business) and the most
    messages a calendar month. Owners only; audited.

    Raises:
        ValidationFailedError: a segment audience without a segment of
            this business.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        campaign_settings_repo: CampaignSettingsRepoContract,
        customer_segment_repo: CustomerSegmentRepoContract,
        audit_log_repo: AuditLogRepoContract,
        reader: CampaignSettingsReader,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._settings_repo: CampaignSettingsRepoContract = campaign_settings_repo
        self._segment_repo: CustomerSegmentRepoContract = customer_segment_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._reader: CampaignSettingsReader = reader
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateCampaignSettingsCommand) -> CampaignSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        request: CampaignSettingsRequest = input_data.request
        self._check_audience(business, request)
        now: Microseconds = self._wall_clock.now_unix()
        settings = stored_or_niche_default(
            self._settings_repo.get_by_business(business.id),
            business,
            self._reader.niche_rule(business),
            now,
        ).model_copy(
            update={
                "is_enabled": request.is_enabled,
                "rule_kind": request.rule_kind,
                "delay_days": request.delay_days,
                "audience": request.audience,
                "segment_id": (
                    request.segment_id
                    if request.audience is CampaignAudience.SEGMENT
                    else None
                ),
                "monthly_cap": request.monthly_cap,
                "updated_by": input_data.user_id,
                "updated_at": now,
            }
        )
        self._settings_repo.save(settings)
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.UPDATE,
                CAMPAIGN_SETTINGS_ENTITY,
                str(settings.id),
                now,
            )
        )
        return self._reader.view(business, settings, now)

    def _check_audience(
        self, business: BusinessDocument, request: CampaignSettingsRequest
    ) -> None:
        if request.audience is not CampaignAudience.SEGMENT:
            return

        if request.segment_id is None or (
            self._segment_repo.get(business.id, request.segment_id) is None
        ):
            raise ValidationFailedError(
                "Choose one of the business's saved segments as the audience."
            )
