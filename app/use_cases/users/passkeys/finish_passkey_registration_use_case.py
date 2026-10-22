from typed_time_provider import Microseconds, WallClock

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
    PasskeyRepoContract,
)
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.mfa import AuthLevel
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument
from app.schemas.dto.passkeys import FinishPasskeyRegistrationCommand, PasskeyAddedView
from app.schemas.typings.mfa.constrained_strings import RecoveryCode
from app.use_cases.shared.second_factors import has_second_factor
from app.use_cases.shared.session_sweeps import own_session
from app.use_cases.users.mfa.mfa_records import audit_mfa_change
from app.use_cases.users.mfa.session_level import record_session_level
from app.use_cases.users.passkeys.passkey_challenges import take_passkey_challenge
from app.use_cases.users.passkeys.passkey_records import PASSKEY_ENTITY, passkey_view
from app.use_cases.users.passkeys.passkey_registration import (
    add_passkey,
    start_second_factor,
)


class FinishPasskeyRegistrationUseCase(
    UseCaseContract[FinishPasskeyRegistrationCommand, PasskeyAddedView]
):
    """
    The browser's new passkey is checked against the person's registration
    challenge (taken once) and stored. As the person's first second
    factor it also brings a new set of recovery codes (shown once), their
    session counts as signed in with two factors from now on, and every
    other session ends (signed in without it). Audited as MFA_CHANGED.
    From the next sign-in on, the passkey is asked after the login code.
    """

    def __init__(
        self,
        passkey_repo: PasskeyRepoContract,
        challenge_repo: PasskeyChallengeRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._challenge_repo: PasskeyChallengeRepoContract = challenge_repo
        self._ceremony: PasskeyCeremonyAdapterContract = ceremony
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: FinishPasskeyRegistrationCommand) -> PasskeyAddedView:
        now: Microseconds = self._wall_clock.now_unix()
        challenge: PasskeyChallengeDocument = take_passkey_challenge(
            self._challenge_repo,
            input_data.passkey_challenge_id,
            input_data.user_id,
            PasskeyCeremonyPurpose.REGISTRATION,
            now,
        )
        is_first_factor: bool = not has_second_factor(
            self._totp_factor_repo, self._passkey_repo, input_data.user_id
        )
        passkey: PasskeyDocument = add_passkey(
            self._passkey_repo,
            self._ceremony,
            challenge,
            input_data.credential,
            input_data.name,
            input_data.user_agent,
            now,
        )
        codes: list[RecoveryCode] = []
        if is_first_factor:
            record_session_level(
                self._session_assurance,
                self._user_session_repo,
                input_data.user_id,
                AuthLevel.TWO_FACTOR,
                now,
            )
            codes = start_second_factor(
                self._recovery_code_repo,
                self._user_session_repo,
                self._audit_log_repo,
                input_data.user_id,
                own_session(self._session_assurance, input_data.user_id),
                input_data.client_ip_address,
                now,
            )
        audit_mfa_change(
            self._audit_log_repo,
            input_data.user_id,
            PASSKEY_ENTITY,
            input_data.client_ip_address,
            now,
        )
        return PasskeyAddedView(passkey=passkey_view(passkey), recovery_codes=codes)
