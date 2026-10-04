from typed_time_provider import Microseconds, WallClock

from app.contracts.mfa import TotpSecretCipherAdapterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.mfa import AuthLevel, TotpFactorStatus
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.dto.mfa import ConfirmTotpCommand, RecoveryCodesView
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.users.mfa.mfa_records import (
    TOTP_FACTOR_ENTITY,
    audit_mfa_change,
    issue_recovery_codes,
)
from app.use_cases.users.mfa.second_factor_check import SecondFactorCheck
from app.use_cases.users.mfa.session_level import record_session_level

NOTHING_TO_CONFIRM_MESSAGE: str = (
    "There is no authenticator being set up. Start setting it up again."
)


class ConfirmTotpEnrollmentUseCase(
    UseCaseContract[ConfirmTotpCommand, RecoveryCodesView]
):
    """
    The first code from the app turns the new authenticator on. The person
    gets a new set of recovery codes (shown once), their current session
    counts as signed in with two factors from now on, and the change is
    audited as MFA_CHANGED. From the next sign-in on, the app's code is
    asked after the login code.
    """

    def __init__(
        self,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        totp_secret_cipher: TotpSecretCipherAdapterContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._check: SecondFactorCheck = SecondFactorCheck(
            totp_factor_repo, recovery_code_repo, totp_secret_cipher
        )

    def run(self, input_data: ConfirmTotpCommand) -> RecoveryCodesView:
        now: Microseconds = self._wall_clock.now_unix()
        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(
            input_data.user_id
        )
        if factor is None or factor.status is not TotpFactorStatus.PENDING:
            raise ConflictError(NOTHING_TO_CONFIRM_MESSAGE)

        self._check.confirm_pending(factor, input_data.code, now)
        recovery_codes = issue_recovery_codes(
            self._recovery_code_repo, input_data.user_id, now
        )
        record_session_level(
            self._session_assurance,
            self._user_session_repo,
            input_data.user_id,
            AuthLevel.TWO_FACTOR,
            now,
        )
        audit_mfa_change(
            self._audit_log_repo,
            input_data.user_id,
            TOTP_FACTOR_ENTITY,
            input_data.client_ip_address,
            now,
        )
        return RecoveryCodesView(recovery_codes=recovery_codes)
