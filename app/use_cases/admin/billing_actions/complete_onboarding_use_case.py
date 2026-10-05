from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.billing_repositories import (
    OnboardingRequestRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.billing import OnboardingRequestStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import OnboardingRequestDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_actions import AdminActionReceipt, CompleteOnboardingCommand
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.admin.billing_actions.account_action_gate import (
    ONBOARDING_REQUEST_ENTITY,
)
from app.use_cases.shared.business_access import require_business


class CompleteOnboardingUseCase(
    UseCaseContract[CompleteOnboardingCommand, AdminActionReceipt]
):
    """
    POST /v1/admin/clients/{business_id}/onboarding-request/done: the
    platform team finished the done-for-you setup the owner asked for; the
    request is DONE and the client's page stops showing it as waiting. Any
    admin who may write notes about clients may mark it (SUPER, BILLING);
    the audit log names who (UPDATE of the onboarding request).

    Raises:
        NotFoundError: the client asked for no done-for-you setup.
        ConflictError: the request is done already.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        business_repo: BusinessRepoContract,
        onboarding_request_repo: OnboardingRequestRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._onboarding_request_repo: OnboardingRequestRepoContract = (
            onboarding_request_repo
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CompleteOnboardingCommand) -> AdminActionReceipt:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.WRITE_CLIENT_NOTES,
            )
        )
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        request: OnboardingRequestDocument | None = (
            self._onboarding_request_repo.get_by_business(business.id)
        )
        if request is None:
            raise NotFoundError("The client asked for no done-for-you setup.")

        if request.status is OnboardingRequestStatus.DONE:
            raise ConflictError("The done-for-you setup is marked done already.")

        now: Microseconds = self._wall_clock.now_unix()
        request.status = OnboardingRequestStatus.DONE
        request.updated_at = now
        self._onboarding_request_repo.save(request)
        entry = AuditLogEntryDocument(
            business_id=business.id,
            actor_id=admin.id,
            action=AuditAction.UPDATE,
            entity=ONBOARDING_REQUEST_ENTITY,
            entity_id=AuditEntityReference(str(request.id)),
            ip_address=input_data.client_ip_address,
            created_at=now,
            updated_at=now,
        )
        self._audit_log_repo.append(entry)
        return AdminActionReceipt(
            business_id=business.id,
            action=entry.action,
            audit_log_entry_id=entry.id,
            occurred_at=now,
        )
