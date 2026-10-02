import logging

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import (
    OtpChallengeRepoContract,
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.dto.users import LoginSessionView, UserView, VerifyOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    RateLimitedError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.users.constrained_integers import OtpAttemptCount
from app.schemas.typings.users.strings import AccessToken
from app.use_cases.users.otp_login.login_check_limits import (
    refuse_too_frequent_code_checks,
)
from app.utilities.security.access_tokens import (
    generate_access_token,
    hash_access_token,
)
from app.utilities.security.one_time_codes import is_otp_code_matching

logger: logging.Logger = logging.getLogger(__name__)
INVALID_CODE_MESSAGE: str = "The login code is wrong or has expired."
LOCKED_CHALLENGE_MESSAGE: str = (
    "Too many wrong codes. Request a new code and try again."
)


class VerifyOtpLoginUseCase(UseCaseContract[VerifyOtpLoginCommand, LoginSessionView]):
    """
    Check a one-time code and sign the person in.

    Checks are limited per challenge and per client network (ten minutes).
    After `otp_max_failed_attempts` wrong codes the challenge is locked:
    every check takes one attempt in one atomic step before the code is
    compared, so parallel guesses cannot all be compared (at most the limit
    are), and a matching code consumes the challenge by compare-and-swap,
    so it opens one session only. The user is found by phone or e-mail, or
    created on first login with the language chosen when the code was
    requested. The platform admin flag follows the admin phone and e-mail
    lists in the settings. The bearer token is returned once; only its
    SHA-256 hash is stored. Every login is audited.
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
    ) -> None:
        self._otp_challenge_repo: OtpChallengeRepoContract = otp_challenge_repo
        self._user_repo: UserRepoContract = user_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._user_view_transformer: TransformerContract[UserDocument, UserView] = (
            user_view_transformer
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )

    def run(self, input_data: VerifyOtpLoginCommand) -> LoginSessionView:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_code_checks(
            self._rate_limit_registry,
            self._app_settings,
            input_data.challenge_id,
            input_data.client_ip_address,
            now,
        )
        challenge: OtpChallengeDocument = self._consume_challenge(input_data, now)
        user, is_new_user = self._find_or_create_user(challenge, now)
        access_token: AccessToken = generate_access_token()
        session = UserSessionDocument(
            user_id=user.id,
            token_hash=hash_access_token(access_token),
            expires_at=self._wall_clock.now_unix_with_delta(
                Seconds(int(self._app_settings.session_lifetime_seconds))
            ),
            created_at=now,
            updated_at=now,
        )
        self._user_session_repo.save(session)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                actor_id=user.id,
                action=AuditAction.LOGIN,
                entity=AuditEntityName("user"),
                entity_id=AuditEntityReference(str(user.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return LoginSessionView(
            access_token=access_token,
            expires_at=session.expires_at,
            user=self._user_view_transformer.transform(user),
            is_new_user=is_new_user,
        )

    def _consume_challenge(
        self,
        input_data: VerifyOtpLoginCommand,
        now: Microseconds,
    ) -> OtpChallengeDocument:
        max_attempts: OtpAttemptCount = self._app_settings.otp_max_failed_attempts
        challenge: OtpChallengeDocument | None = self._otp_challenge_repo.get(
            input_data.challenge_id
        )
        if challenge is None or challenge.is_consumed:
            raise AuthenticationRequiredError(INVALID_CODE_MESSAGE)

        if challenge.failed_attempts >= max_attempts:
            raise RateLimitedError(LOCKED_CHALLENGE_MESSAGE)

        if now >= challenge.expires_at:
            raise AuthenticationRequiredError(INVALID_CODE_MESSAGE)

        # The check counts as failed until the code matches: taking the
        # attempt first lets no more than `max_attempts` checks through.
        attempt: OtpAttemptCount | None = (
            self._otp_challenge_repo.register_failed_attempt(
                challenge.id, max_attempts, now
            )
        )
        if attempt is None:
            raise self._refusal_after_lost_race(challenge)

        if not is_otp_code_matching(challenge.id, input_data.code, challenge.code_hash):
            if attempt >= max_attempts:
                logger.warning(
                    "Login code challenge %s locked after %s wrong codes.",
                    challenge.id,
                    int(attempt),
                )
            raise AuthenticationRequiredError(INVALID_CODE_MESSAGE)

        consumed: OtpChallengeDocument | None = self._otp_challenge_repo.consume(
            challenge.id, now
        )
        if consumed is None:
            # A parallel check with the same right code opened the session.
            raise AuthenticationRequiredError(INVALID_CODE_MESSAGE)

        return consumed

    def _refusal_after_lost_race(
        self,
        challenge: OtpChallengeDocument,
    ) -> AuthenticationRequiredError | RateLimitedError:
        """
        No attempt was left when this check came to take one: parallel
        checks used them up, or one of them consumed the challenge.
        """

        current: OtpChallengeDocument | None = self._otp_challenge_repo.get(
            challenge.id
        )
        if current is None or current.is_consumed:
            return AuthenticationRequiredError(INVALID_CODE_MESSAGE)

        return RateLimitedError(LOCKED_CHALLENGE_MESSAGE)

    def _find_or_create_user(
        self,
        challenge: OtpChallengeDocument,
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
                created_at=now,
            )

        user.is_verified = True
        if user.country_code is None:
            user.country_code = challenge.country_code

        user.is_platform_admin = self._is_listed_platform_admin(user)
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

    def _is_listed_platform_admin(self, user: UserDocument) -> bool:
        return (
            user.phone_number is not None
            and user.phone_number in self._app_settings.platform_admin_phone_numbers
        ) or (
            user.email is not None
            and user.email in self._app_settings.platform_admin_emails
        )
