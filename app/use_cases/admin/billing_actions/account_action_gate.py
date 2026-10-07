"""
What every account action of the platform admin checks first, and the
audit entry it ends with.
"""

from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_actions import AdminActionReceipt
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.billing_records import require_current_subscription
from app.use_cases.shared.business_access import require_business

SUBSCRIPTION_ENTITY: AuditEntityName = AuditEntityName("subscription")
INVOICE_ENTITY: AuditEntityName = AuditEntityName("invoice")
BILLING_CREDIT_ENTITY: AuditEntityName = AuditEntityName("billing_credit")
ONBOARDING_REQUEST_ENTITY: AuditEntityName = AuditEntityName("onboarding_request")


@dataclass(frozen=True)
class AccountActionTarget:
    """The admin acting, the client's business and its current subscription."""

    admin: UserDocument
    business: BusinessDocument
    subscription: SubscriptionDocument


@dataclass(frozen=True)
class AdminActionRecord:
    """What an account action writes to the client's audit log."""

    action: AuditAction
    entity: AuditEntityName
    entity_id: str
    reason: AdminActionReason | None
    client_ip_address: ClientIpAddress | None


class AccountActionGate:
    """
    An account action needs a platform admin who may manage clients'
    billing (SUPER or BILLING; support is refused), a sign-in within the
    step-up window, the client's business and its subscription. The change
    and its audit entry are written in one unit of work.

    Raises:
        AccessDeniedError: not a platform admin of such a role.
        StepUpRequiredError: the session must sign in again first.
        NotFoundError: no such business, or it has no subscription.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work

    def admit(self, user_id: UserId, business_id: BusinessId) -> AccountActionTarget:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=user_id,
                permission=PlatformAdminPermission.MANAGE_CLIENT_BILLING,
            )
        )
        self._step_up.require_recent_authentication()
        business: BusinessDocument = require_business(self._business_repo, business_id)
        return AccountActionTarget(
            admin=admin,
            business=business,
            subscription=require_current_subscription(
                self._subscription_repo, business.id
            ),
        )

    def transaction(self) -> AbstractContextManager[None]:
        """The change and its audit entry commit together (or neither)."""

        if self._unit_of_work is None:
            return nullcontext()

        return self._unit_of_work.unit_of_work()

    def record(
        self,
        target: AccountActionTarget,
        record: AdminActionRecord,
        now: Microseconds,
    ) -> AdminActionReceipt:
        entry = AuditLogEntryDocument(
            business_id=target.business.id,
            actor_id=target.admin.id,
            action=record.action,
            entity=record.entity,
            entity_id=AuditEntityReference(record.entity_id),
            ip_address=record.client_ip_address,
            reason=record.reason,
            created_at=now,
            updated_at=now,
        )
        self._audit_log_repo.append(entry)
        return AdminActionReceipt(
            business_id=target.business.id,
            action=record.action,
            audit_log_entry_id=entry.id,
            occurred_at=now,
        )
