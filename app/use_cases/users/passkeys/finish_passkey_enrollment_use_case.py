from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    MfaChallengeRepoContract,
    RecoveryCodeRepoContract,
)
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
    PasskeyRepoContract,
)
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.support_access import SignInNoticeFacilitatorContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.mfa import AuthLevel
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.domain.passkeys import PasskeyChallengeDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.passkeys import FinishPasskeyEnrollmentCommand
from app.schemas.dto.users import LoginSessionView, UserView
from app.schemas.typings.mfa.constrained_strings import RecoveryCode
from app.use_cases.users.mfa.mfa_challenges import (
    consume_mfa_challenge,
    open_mfa_step,
    take_mfa_attempt,
)
from app.use_cases.users.mfa.mfa_check_limits import refuse_too_frequent_step_answers
from app.use_cases.users.mfa.mfa_records import audit_mfa_change
from app.use_cases.users.passkeys.passkey_challenges import take_passkey_challenge
from app.use_cases.users.passkeys.passkey_records import PASSKEY_ENTITY
from app.use_cases.users.passkeys.passkey_registration import (
    add_passkey,
    start_second_factor,
)
from app.use_cases.users.sign_in_completion import SignInCompletion


class FinishPasskeyEnrollmentUseCase(
    UseCaseContract[FinishPasskeyEnrollmentCommand, LoginSessionView]
):
    """
    A platform admin's first passkey, created while signing in, opens a
    two-factor session. The new passkey is checked against the step's
    enrollment challenge (taken once) and stored; a new set of recovery
    codes comes back with the session (shown once); the admin's earlier
    sessions end (signed in without it; SESSION_REVOKED with the count);
    the change is audited as MFA_CHANGED. Like an answer to the step, it
    counts as one of the step's attempts, and the step opens one session
    only.
    """

    def __init__(
        self,
        mfa_challenge_repo: MfaChallengeRepoContract,
        user_repo: UserRepoContract,
        passkey_repo: PasskeyRepoContract,
        challenge_repo: PasskeyChallengeRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        user_session_repo: UserSessionRepoContract,
        audit_log_repo: AuditLogRepoContract,
        user_view_transformer: TransformerContract[UserDocument, UserView],
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        rate_limit_registry: RequestRateLimitRegistryContract,
        product_events: RecordProductEventFacilitatorContract,
        platform_admins: PlatformAdminRegistryContract,
        sign_in_notices: SignInNoticeFacilitatorContract,
    ) -> None:
        self._mfa_challenge_repo: MfaChallengeRepoContract = mfa_challenge_repo
        self._user_repo: UserRepoContract = user_repo
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._challenge_repo: PasskeyChallengeRepoContract = challenge_repo
        self._ceremony: PasskeyCeremonyAdapterContract = ceremony
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._sign_in: SignInCompletion = SignInCompletion(
            user_session_repo,
            audit_log_repo,
            user_view_transformer,
            app_settings,
            wall_clock,
            product_events,
            platform_admins,
            sign_in_notices,
        )

    def run(self, input_data: FinishPasskeyEnrollmentCommand) -> LoginSessionView:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_step_answers(
            self._rate_limit_registry,
            self._app_settings,
            input_data.mfa_challenge_id,
            input_data.client_ip_address,
            now,
        )
        step, user = open_mfa_step(
            self._mfa_challenge_repo, self._user_repo, input_data.mfa_challenge_id, now
        )

        take_mfa_attempt(self._mfa_challenge_repo, step, now)
        challenge: PasskeyChallengeDocument = take_passkey_challenge(
            self._challenge_repo,
            input_data.passkey_challenge_id,
            user.id,
            PasskeyCeremonyPurpose.SIGN_IN_ENROLLMENT,
            now,
            step.id,
        )
        add_passkey(
            self._passkey_repo,
            self._ceremony,
            challenge,
            input_data.credential,
            input_data.name,
            input_data.user_agent,
            now,
        )
        codes: list[RecoveryCode] = start_second_factor(
            self._recovery_code_repo,
            self._user_session_repo,
            self._audit_log_repo,
            user.id,
            None,
            input_data.client_ip_address,
            now,
        )
        audit_mfa_change(
            self._audit_log_repo,
            user.id,
            PASSKEY_ENTITY,
            input_data.client_ip_address,
            now,
        )
        consume_mfa_challenge(self._mfa_challenge_repo, step, now)
        return self._sign_in.open_session(
            user,
            AuthLevel.TWO_FACTOR,
            step.is_new_user,
            input_data.client_ip_address,
            input_data.user_agent,
            codes,
        )
