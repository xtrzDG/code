from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.utilities.security.platform_admins import is_listed_platform_admin
from app.utilities.security.two_factor_policy import (
    is_two_factor_session,
    mfa_required,
)

TEAM_TWO_FACTOR_MESSAGE: str = (
    "This business asks its team to sign in with two factors: set up an "
    "authenticator app (Account → Security) and sign in again."
)


class AuthorizeBusinessAccessUseCase(
    UseCaseContract[BusinessAccessRequest, BusinessDocument]
):
    """
    Return the business when the user may act on it.

    A business the user is not a member of is reported as missing, not
    forbidden, so foreign ids cannot be probed. Staff asking for an
    owner-only action get AccessDeniedError. When the owner requires two
    factors of the team (`require_mfa_for_members`), a member's session
    signed in with the login code alone gets MfaRequiredError (reason
    `mfa_required`).

    Platform admins pass and leave an ADMIN_ACCESS entry in the audit log
    (concept sections 8 and 10). Admin status is read from the
    PLATFORM_ADMIN_* lists at every call (someone taken off them is refused
    at once), and an admin's session must be signed in with two factors.

    The two-factor rules apply to requests made with a session (the HTTP
    gateway binds it); work in the background (no session bound) acts on
    what such a request already authorized.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        session_assurance: SessionAssuranceContract,
        app_settings: AppSettings,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: BusinessAccessRequest) -> BusinessDocument:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        assurance: SessionAssurance | None = self._session_assurance.current()
        for member in business.members:
            if member.user_id != input_data.user_id:
                continue

            if (
                business.require_mfa_for_members
                and assurance is not None
                and not is_two_factor_session(assurance, input_data.user_id)
            ):
                raise mfa_required(TEAM_TWO_FACTOR_MESSAGE)

            if (
                input_data.required_role is BusinessMemberRole.OWNER
                and member.role is not BusinessMemberRole.OWNER
            ):
                raise AccessDeniedError("Only the business owner may do this.")

            return business

        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if user is not None and self._is_admin_with_two_factors(user, assurance):
            now: Microseconds = self._wall_clock.now_unix()
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=user.id,
                    action=AuditAction.ADMIN_ACCESS,
                    entity=AuditEntityName("business"),
                    entity_id=AuditEntityReference(str(business.id)),
                    created_at=now,
                    updated_at=now,
                )
            )
            return business

        raise NotFoundError(f"Business {input_data.business_id} was not found.")

    def _is_admin_with_two_factors(
        self, user: UserDocument, assurance: SessionAssurance | None
    ) -> bool:
        if not is_listed_platform_admin(user, self._app_settings):
            return False

        return assurance is None or is_two_factor_session(assurance, user.id)
