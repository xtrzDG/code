"""An owner no longer needs the number they asked the team for."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.phone_numbers import PhoneNumberRequestRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.phone_numbers import PhoneNumberRequestStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.phone_numbers import PhoneNumberRequestDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.phone_numbers.phone_line import CancelPhoneNumberRequestCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.channels.phone_numbers.request_phone_number_use_case import (
    REQUEST_ENTITY,
)


class CancelPhoneNumberRequestUseCase(
    UseCaseContract[CancelPhoneNumberRequestCommand, None]
):
    """
    The owner cancels their open request (audited); the team sees it closed.

    Raises:
        NotFoundError: the business has no open request.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        phone_number_request_repo: PhoneNumberRequestRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._request_repo: PhoneNumberRequestRepoContract = phone_number_request_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CancelPhoneNumberRequestCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        request: PhoneNumberRequestDocument | None = self._request_repo.get_by_business(
            business.id
        )
        if request is None or request.status is not PhoneNumberRequestStatus.OPEN:
            raise NotFoundError("There is no open request for a number.")

        now: Microseconds = self._wall_clock.now_unix()
        request.status = PhoneNumberRequestStatus.CANCELLED
        request.closed_at = now
        request.updated_at = now
        self._request_repo.save(request)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=REQUEST_ENTITY,
                entity_id=AuditEntityReference(str(request.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
