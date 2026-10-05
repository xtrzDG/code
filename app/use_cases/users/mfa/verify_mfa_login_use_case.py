from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.mfa import TotpSecretCipherAdapterContract
from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    MfaChallengeRepoContract,
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.support_access import SignInNoticeFacilitatorContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.mfa import AuthLevel, TotpFactorStatus
from app.schemas.constants.users import SessionSweepReason
from app.schemas.domain.mfa import MfaChallengeDocument, TotpFactorDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import VerifyMfaLoginCommand
from app.schemas.dto.sessions import SessionSweep
from app.schemas.dto.users import LoginSessionView, UserView
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ValidationFailedError,
)
from app.schemas.typings.mfa.constrained_strings import RecoveryCode
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.shared.session_sweeps import end_sessions
from app.use_cases.users.mfa.mfa_challenges import (
    EXPIRED_STEP_MESSAGE,
    consume_mfa_challenge,
    open_mfa_challenge,
    take_mfa_attempt,
)
from app.use_cases.users.mfa.mfa_check_limits import (
    refuse_too_frequent_second_factor_checks,
)
from app.use_cases.users.mfa.mfa_records import (
    TOTP_FACTOR_ENTITY,
    audit_mfa_change,
    issue_recovery_codes,
)
from app.use_cases.users.mfa.second_factor_check import SecondFactorCheck
from app.use_cases.users.sign_in_completion import SignInCompletion

SET_UP_FIRST_MESSAGE: str = "Set up your authenticator app first, then enter its code."


class VerifyMfaLoginUseCase(UseCaseContract[VerifyMfaLoginCommand, LoginSessionView]):
    """
    The second step of a sign-in opens a two-factor session.

    A person with an authenticator enters its code or one of their
    recovery codes (SecondFactorCheck). A platform admin without one has
    just set it up (StartMfaLoginEnrollmentUseCase): its first code turns
    it on, a new set of recovery codes comes back with the session (shown
    once), the admin's earlier sessions end (they were signed in without
    it; SESSION_REVOKED with the count) and the change is audited as
    MFA_CHANGED. Checks are limited per
    step and per client network, the step locks after five wrong codes and
    is used by compare-and-swap, so it opens one session only.
    """

    def __init__(
        self,
        mfa_challenge_repo: MfaChallengeRepoContract,
        user_repo: UserRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        totp_secret_cipher: TotpSecretCipherAdapterContract,
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
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._recovery_code_repo: RecoveryCodeRepoContract = recovery_code_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._check: SecondFactorCheck = SecondFactorCheck(
            totp_factor_repo, recovery_code_repo, totp_secret_cipher
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

    def run(self, input_data: VerifyMfaLoginCommand) -> LoginSessionView:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_second_factor_checks(
            self._rate_limit_registry,
            self._app_settings,
            RateLimitKey(f"mfa-check:challenge:{input_data.mfa_challenge_id}"),
            input_data.client_ip_address,
            now,
        )
        challenge: MfaChallengeDocument = open_mfa_challenge(
            self._mfa_challenge_repo, input_data.mfa_challenge_id, now
        )
        user: UserDocument | None = self._user_repo.get(challenge.user_id)
        if user is None:
            raise AuthenticationRequiredError(EXPIRED_STEP_MESSAGE)

        take_mfa_attempt(self._mfa_challenge_repo, challenge, now)
        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(user.id)
        recovery_codes: list[RecoveryCode] | None = None
        if factor is not None and factor.status is TotpFactorStatus.ACTIVE:
            self._check.verify(user.id, input_data.code, input_data.recovery_code, now)
        else:
            recovery_codes = self._finish_enrollment(user, factor, input_data, now)

        consume_mfa_challenge(self._mfa_challenge_repo, challenge, now)
        return self._sign_in.open_session(
            user,
            AuthLevel.TWO_FACTOR,
            challenge.is_new_user,
            input_data.client_ip_address,
            input_data.user_agent,
            recovery_codes,
        )

    def _finish_enrollment(
        self,
        user: UserDocument,
        factor: TotpFactorDocument | None,
        input_data: VerifyMfaLoginCommand,
        now: Microseconds,
    ) -> list[RecoveryCode]:
        if factor is None or input_data.code is None:
            raise ValidationFailedError(SET_UP_FIRST_MESSAGE)

        self._check.confirm_pending(factor, input_data.code, now)
        codes: list[RecoveryCode] = issue_recovery_codes(
            self._recovery_code_repo, user.id, now
        )
        end_sessions(
            self._user_session_repo,
            self._audit_log_repo,
            SessionSweep(
                user_id=user.id,
                actor_id=user.id,
                reason=SessionSweepReason.AUTHENTICATOR_ADDED,
                client_ip_address=input_data.client_ip_address,
                now=now,
            ),
        )
        audit_mfa_change(
            self._audit_log_repo,
            user.id,
            TOTP_FACTOR_ENTITY,
            input_data.client_ip_address,
            now,
        )
        return codes
