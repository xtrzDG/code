from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.client_health import CabinetSection
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import ClientCabinetAccess, OpenClientCabinetCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.users.prefixed_id import UserId


class OpenClientCabinetUseCase(
    UseCaseContract[OpenClientCabinetCommand, ClientCabinetAccess]
):
    """
    A platform admin enters a client's cabinet (concept: "вход в кабинет
    клиента — только с записью в журнал").

    Writes ADMIN_ACCESS to the client's audit log with the admin and the IP
    address, then lists the cabinet sections the admin may open. The cabinet
    endpoints audit every later request of the admin again.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[UserId, UserDocument],
        business_repo: BusinessRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[UserId, UserDocument] = (
            authorize_platform_admin
        )
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OpenClientCabinetCommand) -> ClientCabinetAccess:
        admin: UserDocument = self._authorize_platform_admin.run(input_data.user_id)
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        now: Microseconds = self._wall_clock.now_unix()
        entry = AuditLogEntryDocument(
            business_id=business.id,
            actor_id=admin.id,
            action=AuditAction.ADMIN_ACCESS,
            entity=AuditEntityName("business_cabinet"),
            entity_id=AuditEntityReference(str(business.id)),
            ip_address=input_data.client_ip_address,
            created_at=now,
            updated_at=now,
        )
        self._audit_log_repo.append(entry)
        return ClientCabinetAccess(
            business_id=business.id,
            business_name=business.name,
            country_code=business.country_code,
            owner_language=business.owner_language,
            sections=list(CabinetSection),
            audit_log_entry_id=entry.id,
            opened_at=now,
        )
