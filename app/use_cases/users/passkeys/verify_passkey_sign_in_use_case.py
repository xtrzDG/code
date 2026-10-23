from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import MfaChallengeRepoContract
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
from app.schemas.domain.mfa import MfaChallengeDocument
from app.schemas.domain.passkeys import PasskeyChallengeDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.passkeys import VerifyPasskeySignInCommand
from app.schemas.dto.users import LoginSessionView, UserView
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.exceptions.passkey_errors import PasskeyRejectedError
from app.schemas.typings.mfa.constrained_integers import MfaAttemptCount
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.users.mfa.mfa_challenges import (
    EXPIRED_STEP_MESSAGE,
    MFA_MAX_FAILED_ATTEMPTS,
    consume_mfa_challenge,
    open_mfa_challenge,
    take_mfa_attempt,
)
from app.use_cases.users.mfa.mfa_check_limits import (
    refuse_too_frequent_second_factor_checks,
)
from app.use_cases.users.passkeys.passkey_assertions import PasskeyAssertionCheck
from app.use_cases.users.passkeys.passkey_challenges import take_passkey_challenge
from app.use_cases.users.sign_in_completion import SignInCompletion
from app.use_cases.users.sign_in_security_audit import SignInSecurityAudit


class VerifyPasskeySignInUseCase(
    UseCaseContract[VerifyPasskeySignInCommand, LoginSessionView]
):
    """
    The second step of a sign-in answered with a passkey opens a
    two-factor session. Checks are limited per step and per client network
    (the same budget as authenticator codes); the answer counts as one of
    the step's five attempts before it is checked; the passkey challenge is
    taken once and must belong to this step; the step is used by
    compare-and-swap, so it opens one session only. A refused answer is
    audited as LOGIN_FAILED (MFA_LOCKED on the last attempt), a copied
    authenticator also as MFA_CHANGED (the passkey stops signing).
    """

    def __init__(
        self,
        mfa_challenge_repo: MfaChallengeRepoContract,
        user_repo: UserRepoContract,
        passkey_repo: PasskeyRepoContract,
        challenge_repo: PasskeyChallengeRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
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
        self._challenge_repo: PasskeyChallengeRepoContract = challenge_repo
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._assertion: PasskeyAssertionCheck = PasskeyAssertionCheck(
            passkey_repo, ceremony, audit_log_repo
        )
        self._security_audit: SignInSecurityAudit = SignInSecurityAudit(
            audit_log_repo, user_repo, app_settings
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

    def run(self, input_data: VerifyPasskeySignInCommand) -> LoginSessionView:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_second_factor_checks(
            self._rate_limit_registry,
            self._app_settings,
            RateLimitKey(f"mfa-check:challenge:{input_data.mfa_challenge_id}"),
            input_data.client_ip_address,
            now,
        )
        step: MfaChallengeDocument = open_mfa_challenge(
            self._mfa_challenge_repo, input_data.mfa_challenge_id, now
        )
        user: UserDocument | None = self._user_repo.get(step.user_id)
        if user is None:
            raise AuthenticationRequiredError(EXPIRED_STEP_MESSAGE)

        attempt: MfaAttemptCount = take_mfa_attempt(self._mfa_challenge_repo, step, now)
        try:
            challenge: PasskeyChallengeDocument = take_passkey_challenge(
                self._challenge_repo,
                input_data.passkey_challenge_id,
                user.id,
                PasskeyCeremonyPurpose.SIGN_IN,
                now,
                step.id,
            )
            self._assertion.verify(
                challenge, input_data.credential, input_data.client_ip_address, now
            )
        except PasskeyRejectedError:
            self._security_audit.wrong_second_factor(
                user.id,
                attempt,
                MFA_MAX_FAILED_ATTEMPTS,
                input_data.client_ip_address,
                now,
            )
            raise

        consume_mfa_challenge(self._mfa_challenge_repo, step, now)
        return self._sign_in.open_session(
            user,
            AuthLevel.TWO_FACTOR,
            step.is_new_user,
            input_data.client_ip_address,
            input_data.user_agent,
        )
