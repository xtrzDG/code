from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.notification_repositories import (
    NotificationPreferencesRepoContract,
    PushSubscriptionRepoContract,
)
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.contracts.repositories.security_nudge_repositories import (
    SecurityNudgeRepoContract,
)
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.business_closures.account_deletion import (
    DeleteCurrentUserCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.users.account_deletion.account_departure_checks import (
    require_no_orphans,
)

USER_ENTITY: AuditEntityName = AuditEntityName("user")
MEMBER_ENTITY: AuditEntityName = AuditEntityName("business_member")


class DeleteCurrentUserUseCase(UseCaseContract[DeleteCurrentUserCommand, None]):
    """
    A person deletes their own account (`DELETE /v1/me`, after a fresh
    sign-in). Refused while they are the last owner of a business that is
    not closing, or of a brand, and for a member of the platform team (the
    team removes them first). Otherwise they leave every business and brand
    (each business's log records it), and their sessions (this one too),
    authenticator, recovery codes, passkeys, devices for notifications,
    notification preferences and reminder answers go, then the account
    itself; the platform's audit chain records the deletion. Records of
    businesses they acted in stay those businesses' (an audit entry names
    the person by id only). Each step is safe to repeat.
    """

    def __init__(
        self,
        step_up: StepUpGuardContract,
        storage_scope: StorageScopeContract,
        user_repo: UserRepoContract,
        user_session_repo: UserSessionRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        passkey_repo: PasskeyRepoContract,
        business_repo: BusinessRepoContract,
        brand_repo: BrandRepoContract,
        closure_repo: BusinessClosureRepoContract,
        push_subscription_repo: PushSubscriptionRepoContract,
        notification_preferences_repo: NotificationPreferencesRepoContract,
        security_nudge_repo: SecurityNudgeRepoContract,
        platform_admins: PlatformAdminRegistryContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._step_up: StepUpGuardContract = step_up
        self._storage_scope: StorageScopeContract = storage_scope
        self._user_repo: UserRepoContract = user_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._brand_repo: BrandRepoContract = brand_repo
        self._closure_repo: BusinessClosureRepoContract = closure_repo
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )
        self._preferences_repo: NotificationPreferencesRepoContract = (
            notification_preferences_repo
        )
        self._security_nudge_repo: SecurityNudgeRepoContract = security_nudge_repo
        self._platform_admins: PlatformAdminRegistryContract = platform_admins
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DeleteCurrentUserCommand) -> None:
        self._step_up.require_recent_authentication()
        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if user is None:
            raise NotFoundError("The account was not found.")

        if user.is_platform_admin or self._platform_admins.role_of(user) is not None:
            raise ConflictError(
                "A member of the platform team leaves the team (Admin → Team) "
                "before deleting the account."
            )

        now: Microseconds = self._wall_clock.now_unix()
        with self._storage_scope.platform_wide():
            businesses: list[BusinessDocument] = self._business_repo.list_by_member(
                user.id
            )
            brands: list[BrandDocument] = self._brand_repo.list_by_member(user.id)
            require_no_orphans(user.id, businesses, brands, self._closure_repo)
            for business in businesses:
                self._leave_business(business.id, input_data, now)
            for brand in brands:
                self._leave_brand(brand, user.id, now)

        self._forget_sign_in(user.id)
        self._user_repo.delete(user.id)
        self._audit(None, USER_ENTITY, input_data, now)

    def _leave_business(
        self,
        business_id: BusinessId,
        input_data: DeleteCurrentUserCommand,
        now: Microseconds,
    ) -> None:
        user_id: UserId = input_data.user_id

        def leave(current: BusinessDocument) -> None:
            current.members = [
                member for member in current.members if member.user_id != user_id
            ]
            current.updated_at = now

        self._business_repo.update(business_id, leave)
        for device in self._push_subscription_repo.list_by_user(business_id, user_id):
            self._push_subscription_repo.delete(business_id, device.id)
        self._preferences_repo.delete(business_id, user_id)
        self._security_nudge_repo.forget(business_id, user_id)
        self._audit(business_id, MEMBER_ENTITY, input_data, now)

    def _leave_brand(
        self, brand: BrandDocument, user_id: UserId, now: Microseconds
    ) -> None:
        def leave(current: BrandDocument) -> None:
            current.members = [
                member for member in current.members if member.user_id != user_id
            ]
            current.updated_at = now

        self._brand_repo.update(brand.id, leave)

    def _forget_sign_in(self, user_id: UserId) -> None:
        self._user_session_repo.delete_for_user(user_id)
        self._totp_factor_repo.delete_for_user(user_id)
        self._recovery_code_repo.delete_for_user(user_id)
        for passkey in self._passkey_repo.list_for_user(user_id):
            self._passkey_repo.delete(passkey.id)

    def _audit(
        self,
        business_id: BusinessId | None,
        entity: AuditEntityName,
        input_data: DeleteCurrentUserCommand,
        now: Microseconds,
    ) -> None:
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business_id,
                actor_id=input_data.user_id,
                action=AuditAction.DELETE,
                entity=entity,
                entity_id=AuditEntityReference(str(input_data.user_id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
