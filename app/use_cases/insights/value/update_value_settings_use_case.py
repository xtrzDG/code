from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.value_settings import ValueSettingsDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.value_views import (
    UpdateValueSettingsCommand,
    ValueSettingsView,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.insights.value.value_estimates import (
    EstimateCatalogs,
    estimate_business_value,
)
from app.use_cases.insights.value.value_settings_views import (
    build_value_settings_view,
    stored_settings_or_new,
)

VALUE_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("value_settings")


class UpdateValueSettingsUseCase(
    UseCaseContract[UpdateValueSettingsCommand, ValueSettingsView]
):
    """
    The owner sets the average check of the money estimate, or clears it
    (the niche's typical check is used again). Reports already stored keep
    the check they used. Audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        catalogs: EstimateCatalogs,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._catalogs: EstimateCatalogs = catalogs
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateValueSettingsCommand) -> ValueSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        settings: ValueSettingsDocument = stored_settings_or_new(
            business, self._catalogs.value_settings_repo.get_by_business(business.id)
        )
        settings.average_check_minor = input_data.request.average_check_minor
        settings.updated_at = now
        self._catalogs.value_settings_repo.save(settings)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=VALUE_SETTINGS_ENTITY,
                entity_id=AuditEntityReference(str(settings.id)),
                created_at=now,
                updated_at=now,
            )
        )
        return build_value_settings_view(
            business, settings, estimate_business_value(self._catalogs, business)
        )
