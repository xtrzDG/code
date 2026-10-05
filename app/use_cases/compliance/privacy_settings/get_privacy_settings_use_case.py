from app.contracts.processor_erasure import ProcessorErasureFacilitatorContract
from app.contracts.repositories.retention_repositories import (
    BusinessPrivacySettingsRepoContract,
    RetentionPurgeStateRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.retention import PrivacySettingsQuery, PrivacySettingsView
from app.use_cases.compliance.privacy_settings.privacy_settings_views import (
    build_privacy_settings_view,
)


class GetPrivacySettingsUseCase(
    UseCaseContract[PrivacySettingsQuery, PrivacySettingsView]
):
    """
    Settings → Privacy for the owner: how long conversations and the
    records of model calls are kept (the defaults until changed), how long
    call recordings are kept, what the latest retention purge removed, and
    which sub-processors delete their copies with the platform's own.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        privacy_settings_repo: BusinessPrivacySettingsRepoContract,
        purge_state_repo: RetentionPurgeStateRepoContract,
        processor_erasure: ProcessorErasureFacilitatorContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._privacy_settings_repo: BusinessPrivacySettingsRepoContract = (
            privacy_settings_repo
        )
        self._purge_state_repo: RetentionPurgeStateRepoContract = purge_state_repo
        self._processor_erasure: ProcessorErasureFacilitatorContract = processor_erasure

    def run(self, input_data: PrivacySettingsQuery) -> PrivacySettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return build_privacy_settings_view(
            business,
            self._privacy_settings_repo.get_or_default(business.id),
            self._purge_state_repo,
            self._processor_erasure,
        )
