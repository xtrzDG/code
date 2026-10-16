from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import SessionSweepReason
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.dto.mfa import MfaChangeCommand
from app.schemas.dto.sessions import SessionSweep
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.use_cases.shared.session_sweeps import lower_sessions
from app.use_cases.users.mfa.mfa_records import TOTP_FACTOR_ENTITY, audit_mfa_change


class RemoveTotpFactorUseCase(UseCaseContract[MfaChangeCommand, None]):
    """
    The person removes their authenticator (a new phone, a lost app),
    after confirming it is them (step-up): its recovery codes go with it,
    and every session of theirs (this one and those on other devices)
    counts as one factor again, so no session keeps two-factor rights the
    person can no longer prove. The change is audited as MFA_CHANGED with
    how many sessions were lowered. A platform admin is asked to set up a
    new authenticator at their next sign-in; until then the admin pages
    refuse all their sessions.
    """

    def __init__(
        self,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        user_session_repo: UserSessionRepoContract,
        step_up: StepUpGuardContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
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
        lowered: DocumentCount = lower_sessions(
            self._user_session_repo,
            SessionSweep(
                user_id=input_data.user_id,
                actor_id=input_data.user_id,
                reason=SessionSweepReason.AUTHENTICATOR_REMOVED,
                client_ip_address=input_data.client_ip_address,
                now=now,
            ),
        )
        audit_mfa_change(
            self._audit_log_repo,
            input_data.user_id,
            TOTP_FACTOR_ENTITY,
            input_data.client_ip_address,
            now,
            lowered,
        )
