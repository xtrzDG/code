from typed_time_provider import Microseconds, WallClock

from app.contracts.processor_erasure import ProcessorErasureFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.retention_repositories import (
    BusinessPrivacySettingsRepoContract,
    RetentionPurgeStateRepoContract,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.retention import PrivacySettingsView, UpdatePrivacySettingsCommand
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.compliance.privacy_settings.privacy_settings_views import (
    build_privacy_settings_view,
)

PRIVACY_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("privacy_settings")


class UpdatePrivacySettingsUseCase(
    UseCaseContract[UpdatePrivacySettingsCommand, PrivacySettingsView]
):
    """
    The owner chooses how long conversations (30 days to 10 years) and the
    records of model calls (up to 30 days) are kept. A shorter period
    deletes data at the next nightly purge, so it asks for a recent
    sign-in (step-up) first; a longer one keeps only what is still there.
    Audited with the owner and their address.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        privacy_settings_repo: BusinessPrivacySettingsRepoContract,
        purge_state_repo: RetentionPurgeStateRepoContract,
        processor_erasure: ProcessorErasureFacilitatorContract,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._privacy_settings_repo: BusinessPrivacySettingsRepoContract = (
            privacy_settings_repo
        )
        self._purge_state_repo: RetentionPurgeStateRepoContract = purge_state_repo
        self._processor_erasure: ProcessorErasureFacilitatorContract = processor_erasure
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdatePrivacySettingsCommand) -> PrivacySettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        settings: BusinessPrivacySettingsDocument = (
            self._privacy_settings_repo.get_or_default(business.id)
        )
        request = input_data.request
        is_shorter: bool = int(request.conversation_retention_days) < int(
            settings.conversation_retention_days
        ) or int(request.llm_turn_retention_days) < int(
            settings.llm_turn_retention_days
        )
        if is_shorter:
            self._step_up.require_recent_authentication()

        now: Microseconds = self._wall_clock.now_unix()
        settings.conversation_retention_days = request.conversation_retention_days
        settings.llm_turn_retention_days = request.llm_turn_retention_days
        settings.updated_at = now
        self._privacy_settings_repo.save(settings)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=PRIVACY_SETTINGS_ENTITY,
                entity_id=AuditEntityReference(str(settings.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return build_privacy_settings_view(
            business, settings, self._purge_state_repo, self._processor_erasure
        )
