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
from app.schemas.constants.mfa import TotpFactorStatus
from app.schemas.constants.users import SessionSweepReason
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.dto.mfa import MfaChangeCommand, RecoveryCodesView
from app.schemas.dto.sessions import SessionSweep
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.use_cases.shared.session_sweeps import lower_sessions, own_session
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
    not, after the person confirms it is them (step-up). A session opened
    with an old code (a stolen sheet) must not keep two-factor rights, so
    every other session of theirs counts as one factor until it confirms
    again with the authenticator; the request's own session, which has
    just confirmed, stays as it is. Audited as MFA_CHANGED with how many
    sessions were lowered.
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

    def run(self, input_data: MfaChangeCommand) -> RecoveryCodesView:
        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(
            input_data.user_id
        )
        if factor is None or factor.status is not TotpFactorStatus.ACTIVE:
            raise ConflictError(NO_AUTHENTICATOR_MESSAGE)

        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        codes = issue_recovery_codes(self._recovery_code_repo, input_data.user_id, now)
        lowered: DocumentCount = lower_sessions(
            self._user_session_repo,
            SessionSweep(
                user_id=input_data.user_id,
                actor_id=input_data.user_id,
                reason=SessionSweepReason.RECOVERY_CODES_REPLACED,
                kept_session_id=own_session(
                    self._session_assurance, input_data.user_id
                ),
                client_ip_address=input_data.client_ip_address,
                now=now,
            ),
        )
        audit_mfa_change(
            self._audit_log_repo,
            input_data.user_id,
            RECOVERY_CODES_ENTITY,
            input_data.client_ip_address,
            now,
            lowered,
        )
        return RecoveryCodesView(recovery_codes=codes)
