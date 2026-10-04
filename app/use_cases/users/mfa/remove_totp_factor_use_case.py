from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.dto.mfa import MfaChangeCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.users.mfa.mfa_records import TOTP_FACTOR_ENTITY, audit_mfa_change
from app.use_cases.users.mfa.session_level import record_session_level


class RemoveTotpFactorUseCase(UseCaseContract[MfaChangeCommand, None]):
    """
    The person removes their authenticator (a new phone, a lost app),
    after confirming it is them (step-up): its recovery codes go with it,
    the current session counts as one factor again, and the change is
    audited as MFA_CHANGED. A platform admin is asked to set up a new one
    at their next sign-in; until then the admin pages refuse the session.
    """

    def __init__(
        self,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        step_up: StepUpGuardContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._step_up: StepUpGuardContract = step_up
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: MfaChangeCommand) -> None:
        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(
            input_data.user_id
        )
        if factor is None:
            raise NotFoundError("No authenticator is set up.")

        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        self._totp_factor_repo.delete_for_user(input_data.user_id)
        self._recovery_code_repo.delete_for_user(input_data.user_id)
        record_session_level(
            self._session_assurance,
            self._user_session_repo,
            input_data.user_id,
            AuthLevel.ONE_FACTOR,
            None,
        )
        audit_mfa_change(
            self._audit_log_repo,
            input_data.user_id,
            TOTP_FACTOR_ENTITY,
            input_data.client_ip_address,
            now,
        )
