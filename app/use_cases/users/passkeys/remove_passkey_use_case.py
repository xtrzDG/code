from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import SessionSweepReason
from app.schemas.domain.passkeys import PasskeyDocument
from app.schemas.dto.passkeys import RemovePasskeyCommand
from app.schemas.dto.sessions import SessionSweep
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.use_cases.shared.second_factors import has_second_factor
from app.use_cases.shared.session_sweeps import lower_sessions
from app.use_cases.users.mfa.mfa_records import audit_mfa_change
from app.use_cases.users.passkeys.passkey_records import PASSKEY_ENTITY
from app.use_cases.users.passkeys.rename_passkey_use_case import NOT_FOUND_MESSAGE


class RemovePasskeyUseCase(UseCaseContract[RemovePasskeyCommand, None]):
    """
    The person removes one of their passkeys (a lost phone, a copy
    suspected), after confirming it is them (step-up). While another
    second factor is left (a passkey or the authenticator app) nothing else
    changes. Without one, the recovery codes go too and every session of
    theirs counts as one factor again, so none keeps two-factor rights the
    person can no longer prove. Audited as MFA_CHANGED with how many
    sessions were lowered.
    """

    def __init__(
        self,
        passkey_repo: PasskeyRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        user_session_repo: UserSessionRepoContract,
        step_up: StepUpGuardContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._step_up: StepUpGuardContract = step_up
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RemovePasskeyCommand) -> None:
        passkey: PasskeyDocument | None = self._passkey_repo.get(input_data.passkey_id)
        if passkey is None or passkey.user_id != input_data.user_id:
            raise NotFoundError(NOT_FOUND_MESSAGE)

        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        if not self._passkey_repo.delete(passkey.id):
            raise NotFoundError(NOT_FOUND_MESSAGE)

        lowered: DocumentCount | None = None
        if not has_second_factor(
            self._totp_factor_repo, self._passkey_repo, input_data.user_id
        ):
            self._recovery_code_repo.delete_for_user(input_data.user_id)
            lowered = lower_sessions(
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
            PASSKEY_ENTITY,
            input_data.client_ip_address,
            now,
            lowered,
        )
