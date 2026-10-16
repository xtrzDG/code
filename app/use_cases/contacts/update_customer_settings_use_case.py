from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.customer_settings import (
    CustomerSettingsView,
    UpdateCustomerSettingsCommand,
)
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.contacts.get_customer_settings_use_case import settings_view

SETTINGS_ENTITY: AuditEntityName = AuditEntityName("customer_settings")


class UpdateCustomerSettingsUseCase(
    UseCaseContract[UpdateCustomerSettingsCommand, CustomerSettingsView]
):
    """
    The owner lets staff see customers' phone numbers, or masks them again
    (who sees personal data changes, so it is audited: UPDATE of
    customer_settings). Owners only.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        customer_settings_repo: CustomerSettingsRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._customer_settings_repo: CustomerSettingsRepoContract = (
            customer_settings_repo
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateCustomerSettingsCommand) -> CustomerSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        sees: bool = input_data.request.staff_sees_phone_numbers

        def change(settings: CustomerSettingsDocument) -> None:
            settings.staff_sees_phone_numbers = sees

        changed: CustomerSettingsDocument = self._customer_settings_repo.change(
            business.id, change, now
        )
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=SETTINGS_ENTITY,
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return settings_view(changed)
