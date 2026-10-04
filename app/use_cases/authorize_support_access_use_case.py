from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.support_access import SupportAccessGrantRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import (
    BusinessAccessMode,
    PlatformAdminPermission,
    PlatformAdminRole,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.support_access import SupportAccessCheck
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.shared.support_access import live_sessions, live_write_consent
from app.utilities.security.admin_permissions import has_permission
from app.utilities.security.support_refusals import (
    support_access_required,
    support_read_only,
)
from app.utilities.security.two_factor_policy import is_two_factor_session

BUSINESS_ENTITY: AuditEntityName = AuditEntityName("business")


class AuthorizeSupportAccessUseCase(
    UseCaseContract[SupportAccessCheck, SupportAccessGrantDocument]
):
    """
    May a platform admin who is not a member act on the business now?

    - Only admins whose role opens client cabinets (SUPER, SUPPORT_READONLY;
      read from the admin team at every call) with a session signed in with
      two factors; anyone else gets NotFoundError, as for a foreign id.
    - Only during an open look into this cabinet (the hour after "Open
      cabinet" with a reason): without one, AccessDeniedError with the
      reason `support_access_required`.
    - Reading only, unless the owner's consent to changes is in force and
      the admin's role may change client cabinets (SUPER): a change
      without both gets AccessDeniedError with the reason
      `support_read_only`. Even then support changes what staff may, never
      an owner-only action (billing, team, publishing, security). Each
      change is audited (ADMIN_ACCESS with the address); reads are covered
      by SUPPORT_ACCESS_START.

    Work in the background (no session bound) acts on what a request
    already authorized: it needs a live grant, and reads.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        platform_admins: PlatformAdminRegistryContract,
        grant_repo: SupportAccessGrantRepoContract,
        audit_log_repo: AuditLogRepoContract,
        session_assurance: SessionAssuranceContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._platform_admins: PlatformAdminRegistryContract = platform_admins
        self._grant_repo: SupportAccessGrantRepoContract = grant_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SupportAccessCheck) -> SupportAccessGrantDocument:
        assurance: SessionAssurance | None = self._session_assurance.current()
        role: PlatformAdminRole | None = self._role_with_two_factors(
            input_data, assurance
        )
        if not has_permission(role, PlatformAdminPermission.OPEN_CLIENT_CABINET):
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        now: Microseconds = self._wall_clock.now_unix()
        grants: list[SupportAccessGrantDocument] = self._grant_repo.list_open(
            input_data.business_id
        )
        own: list[SupportAccessGrantDocument] = [
            grant
            for grant in live_sessions(grants, now)
            if grant.admin_user_id == input_data.user_id
        ]
        if not own:
            raise support_access_required()

        mode: BusinessAccessMode = input_data.access_mode or (
            assurance.access_mode if assurance is not None else BusinessAccessMode.READ
        )
        if mode is BusinessAccessMode.WRITE:
            if live_write_consent(grants, now) is None or not has_permission(
                role, PlatformAdminPermission.CHANGE_CLIENT_CABINET
            ):
                raise support_read_only()

            if input_data.required_role is BusinessMemberRole.OWNER:
                raise AccessDeniedError("Only the business owner may do this.")

            self._audit_change(input_data, assurance, now)

        return own[0]

    def _role_with_two_factors(
        self, check: SupportAccessCheck, assurance: SessionAssurance | None
    ) -> PlatformAdminRole | None:
        user: UserDocument | None = self._user_repo.get(check.user_id)
        if user is None:
            return None

        if assurance is not None and not is_two_factor_session(assurance, user.id):
            return None

        return self._platform_admins.role_of(user)

    def _audit_change(
        self,
        check: SupportAccessCheck,
        assurance: SessionAssurance | None,
        now: Microseconds,
    ) -> None:
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=check.business_id,
                actor_id=check.user_id,
                action=AuditAction.ADMIN_ACCESS,
                entity=BUSINESS_ENTITY,
                entity_id=AuditEntityReference(str(check.business_id)),
                ip_address=None if assurance is None else assurance.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
