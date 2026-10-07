"""Checking a login code against its challenge, once (sign-in and step-up)."""

import logging

from typed_time_provider import Microseconds

from app.contracts.repositories.user_repositories import OtpChallengeRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    RateLimitedError,
)
from app.schemas.typings.users.constrained_integers import OtpAttemptCount
from app.schemas.typings.users.constrained_strings import OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.utilities.security.one_time_codes import is_otp_code_matching

logger: logging.Logger = logging.getLogger(__name__)
INVALID_CODE_MESSAGE: str = "The login code is wrong or has expired."
LOCKED_CHALLENGE_MESSAGE: str = (
    "Too many wrong codes. Request a new code and try again."
)


def consume_login_challenge(
    otp_challenge_repo: OtpChallengeRepoContract,
    app_settings: AppSettings,
    challenge_id: OtpChallengeId,
    code: OtpCode,
    now: Microseconds,
) -> OtpChallengeDocument:
    """
    The challenge, consumed, when the code matches it.

    After `otp_max_failed_attempts` wrong codes the challenge is locked:
    every check takes one attempt in one atomic step before the code is
    compared, so parallel guesses cannot all be compared (at most the limit
    are), and a matching code consumes the challenge by compare-and-swap,
    so it serves one sign-in (or one confirmation) only.

    Raises:
        AuthenticationRequiredError: unknown, used, expired or wrong.
        RateLimitedError: the challenge is locked.
    """

    max_attempts: OtpAttemptCount = app_settings.otp_max_failed_attempts
    challenge: OtpChallengeDocument | None = otp_challenge_repo.get(challenge_id)
    if challenge is None or challenge.is_consumed:
        raise AuthenticationRequiredError(INVALID_CODE_MESSAGE)

    if challenge.failed_attempts >= max_attempts:
        raise RateLimitedError(LOCKED_CHALLENGE_MESSAGE)

    if now >= challenge.expires_at:
        raise AuthenticationRequiredError(INVALID_CODE_MESSAGE)

    # The check counts as failed until the code matches: taking the attempt
    # first lets no more than `max_attempts` checks through.
    attempt: OtpAttemptCount | None = otp_challenge_repo.register_failed_attempt(
        challenge.id, max_attempts, now
    )
    if attempt is None:
        raise refusal_after_lost_race(otp_challenge_repo, challenge)

    if not is_otp_code_matching(challenge.id, code, challenge.code_hash):
        if attempt >= max_attempts:
            logger.warning(
                "Login code challenge %s locked after %s wrong codes.",
                challenge.id,
                int(attempt),
            )
        raise AuthenticationRequiredError(INVALID_CODE_MESSAGE)

    consumed: OtpChallengeDocument | None = otp_challenge_repo.consume(
        challenge.id, now
    )
    if consumed is None:
        # A parallel check with the same right code used it.
        raise AuthenticationRequiredError(INVALID_CODE_MESSAGE)

    return consumed


def refusal_after_lost_race(
    otp_challenge_repo: OtpChallengeRepoContract,
    challenge: OtpChallengeDocument,
) -> AuthenticationRequiredError | RateLimitedError:
    """
    No attempt was left when this check came to take one: parallel checks
    used them up, or one of them consumed the challenge.
    """

    current: OtpChallengeDocument | None = otp_challenge_repo.get(challenge.id)
    if current is None or current.is_consumed:
        return AuthenticationRequiredError(INVALID_CODE_MESSAGE)

    return RateLimitedError(LOCKED_CHALLENGE_MESSAGE)
