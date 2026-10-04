from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.mfa import TotpFactorStatus
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.dto.mfa import MfaChangeCommand, RecoveryCodesView
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.users.mfa.mfa_records import (
    RECOVERY_CODES_ENTITY,
    audit_mfa_change,
    issue_recovery_codes,
)

NO_AUTHENTICATOR_MESSAGE: str = (
    "Recovery codes come with an authenticator; set one up first."
)


class RegenerateRecoveryCodesUseCase(
    UseCaseContract[MfaChangeCommand, RecoveryCodesView]
):
    """
    A new set of recovery codes (shown once) replaces the old one, used or
    not, after the person confirms it is them (step-up); audited as
    MFA_CHANGED.
    """

    def __init__(
        self,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        step_up: StepUpGuardContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._step_up: StepUpGuardContract = step_up
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: MfaChangeCommand) -> RecoveryCodesView:
        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(
            input_data.user_id
        )
        if factor is None or factor.status is not TotpFactorStatus.ACTIVE:
            raise ConflictError(NO_AUTHENTICATOR_MESSAGE)

        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        codes = issue_recovery_codes(self._recovery_code_repo, input_data.user_id, now)
        audit_mfa_change(
            self._audit_log_repo,
            input_data.user_id,
            RECOVERY_CODES_ENTITY,
            input_data.client_ip_address,
            now,
        )
        return RecoveryCodesView(recovery_codes=codes)
