from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.mfa_repositories import (
    MfaChallengeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.user_repositories import (
    OtpChallengeRepoContract,
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.support_access import SignInNoticeFacilitatorContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.mfa import AuthLevel, TotpFactorStatus
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.domain.signup_attribution import SignupAttribution
from app.schemas.domain.users import OtpChallengeDocument, UserDocument
from app.schemas.dto.mfa_login import MfaChallengeView, MfaRequiredView
from app.schemas.dto.users import LoginSessionView, UserView, VerifyOtpLoginCommand
from app.use_cases.users.mfa.mfa_challenges import issue_mfa_challenge
from app.use_cases.users.otp_login.login_challenge_consumption import (
    consume_login_challenge,
)
from app.use_cases.users.otp_login.login_check_limits import (
    refuse_too_frequent_code_checks,
)
from app.use_cases.users.sign_in_completion import SignInCompletion


class VerifyOtpLoginUseCase(
    UseCaseContract[VerifyOtpLoginCommand, LoginSessionView | MfaRequiredView]
):
    """
    Check a one-time code and sign the person in.

    Checks are limited per challenge and per client network (ten minutes),
    and a challenge is locked after `otp_max_failed_attempts` wrong codes
    (`consume_login_challenge`). The user is found by phone or e-mail, or
    created on first login with the language chosen when the code was
    requested; the stored platform admin flag follows the admin lists.

    A person with an authenticator, and every platform admin (who sets one
    up then if they have none), gets no session yet: the answer is
    `mfa_required` with a five-minute second step, and
    VerifyMfaLoginUseCase opens a two-factor session. Everyone else gets a
    one-factor session at once (SignInCompletion: the token is returned
    once, only its hash is stored, the login is audited and counted). A new
    account keeps where its owner came from (the cabinet's attribution,
    never changed later).
    """

    def __init__(
        self,
        otp_challenge_repo: OtpChallengeRepoContract,
        user_repo: UserRepoContract,
        user_session_repo: UserSessionRepoContract,
        audit_log_repo: AuditLogRepoContract,
        user_view_transformer: TransformerContract[UserDocument, UserView],
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        rate_limit_registry: RequestRateLimitRegistryContract,
        product_events: RecordProductEventFacilitatorContract,
        platform_admins: PlatformAdminRegistryContract,
        sign_in_notices: SignInNoticeFacilitatorContract,
        totp_factor_repo: TotpFactorRepoContract,
        mfa_challenge_repo: MfaChallengeRepoContract,
    ) -> None:
        self._otp_challenge_repo: OtpChallengeRepoContract = otp_challenge_repo
        self._user_repo: UserRepoContract = user_repo
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._mfa_challenge_repo: MfaChallengeRepoContract = mfa_challenge_repo
        self._platform_admins: PlatformAdminRegistryContract = platform_admins
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

    def run(
        self, input_data: VerifyOtpLoginCommand
    ) -> LoginSessionView | MfaRequiredView:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_code_checks(
            self._rate_limit_registry,
            self._app_settings,
            input_data.challenge_id,
            input_data.client_ip_address,
            now,
        )
        challenge: OtpChallengeDocument = consume_login_challenge(
            self._otp_challenge_repo,
            self._app_settings,
            input_data.challenge_id,
            input_data.code,
            now,
        )
        user, is_new_user = self._find_or_create_user(
            challenge, input_data.signup_attribution, now
        )
        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(user.id)
        has_active_factor: bool = (
            factor is not None and factor.status is TotpFactorStatus.ACTIVE
        )
        if has_active_factor or user.is_platform_admin:
            mfa_challenge: MfaChallengeView = issue_mfa_challenge(
                self._mfa_challenge_repo,
                self._wall_clock,
                user.id,
                is_new_user,
                input_data.client_ip_address,
                requires_enrollment=not has_active_factor,
            )
            return MfaRequiredView(mfa_challenge=mfa_challenge, is_new_user=is_new_user)

        return self._sign_in.open_session(
            user,
            AuthLevel.ONE_FACTOR,
            is_new_user,
            input_data.client_ip_address,
            input_data.user_agent,
        )

    def _find_or_create_user(
        self,
        challenge: OtpChallengeDocument,
        signup_attribution: SignupAttribution | None,
        now: Microseconds,
    ) -> tuple[UserDocument, bool]:
        user: UserDocument | None = self._find_user(challenge)
        is_new_user: bool = user is None
        if user is None:
            user = UserDocument(
                login_method=challenge.login_method,
                phone_number=challenge.phone_number,
                email=challenge.email,
                country_code=challenge.country_code,
                locale=challenge.locale,
                signup_attribution=signup_attribution,
                created_at=now,
            )

        user.is_verified = True
        if user.country_code is None:
            user.country_code = challenge.country_code

        user.is_platform_admin = self._platform_admins.role_of(user) is not None
        user.updated_at = now
        self._user_repo.save(user)
        return user, is_new_user

    def _find_user(self, challenge: OtpChallengeDocument) -> UserDocument | None:
        if challenge.login_method is LoginMethod.PHONE:
            if challenge.phone_number is None:
                return None

            return self._user_repo.find_by_phone_number(challenge.phone_number)

        if challenge.email is None:
            return None

        return self._user_repo.find_by_email(challenge.email)
