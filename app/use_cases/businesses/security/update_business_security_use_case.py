from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.mfa import (
    BusinessSecurityView,
    SessionAssurance,
    UpdateBusinessSecurityCommand,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.businesses.security.business_security_views import (
    build_business_security_view,
)
from app.utilities.security.two_factor_policy import (
    is_two_factor_session,
    mfa_required,
)

OWN_TWO_FACTOR_FIRST_MESSAGE: str = (
    "Set up two-factor sign-in for yourself first (Account → Security), so "
    "the requirement does not lock you out."
)


class UpdateBusinessSecurityUseCase(
    UseCaseContract[UpdateBusinessSecurityCommand, BusinessSecurityView]
):
    """
    The owner asks the whole team (owners included) to sign in with two
    factors, or stops asking. Like every team change it needs a recent
    sign-in or confirmation (step-up), and turning it on needs the owner's
    own session to be signed in with two factors, so nobody locks
    themselves out. From the next request on, members whose session was
    signed in with the login code alone are refused (`mfa_required`).
    Audited (entity `business_security`).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        business_repo: BusinessRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        session_assurance: SessionAssuranceContract,
        step_up: StepUpGuardContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._business_repo: BusinessRepoContract = business_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._step_up: StepUpGuardContract = step_up
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateBusinessSecurityCommand) -> BusinessSecurityView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        self._step_up.require_recent_authentication()
        assurance: SessionAssurance | None = self._session_assurance.current()
        if input_data.require_mfa_for_members and not is_two_factor_session(
            assurance, input_data.user_id
        ):
            raise mfa_required(OWN_TWO_FACTOR_FIRST_MESSAGE)

        def apply(current: BusinessDocument) -> None:
            current.require_mfa_for_members = input_data.require_mfa_for_members

        stored: BusinessDocument = self._business_repo.update(business.id, apply)
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=AuditEntityName("business_security"),
                entity_id=AuditEntityReference(str(business.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return build_business_security_view(
            stored, self._totp_factor_repo, assurance, input_data.user_id
        )
