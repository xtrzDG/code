"""The second step of a sign-in: issuing it, and checking it once."""

import logging

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.repositories.mfa_repositories import MfaChallengeRepoContract
from app.schemas.domain.mfa import MfaChallengeDocument
from app.schemas.dto.mfa_login import MfaChallengeView
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    RateLimitedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.mfa.constrained_integers import (
    MfaAttemptCount,
    MfaChallengeLifetimeSeconds,
)
from app.schemas.typings.mfa.prefixed_id import MfaChallengeId
from app.schemas.typings.users.booleans import IsNewUser
from app.schemas.typings.users.prefixed_id import UserId

logger: logging.Logger = logging.getLogger(__name__)
MFA_CHALLENGE_LIFETIME: MfaChallengeLifetimeSeconds = MfaChallengeLifetimeSeconds(
    5 * 60
)
MFA_MAX_FAILED_ATTEMPTS: MfaAttemptCount = MfaAttemptCount(5)
EXPIRED_STEP_MESSAGE: str = (
    "This sign-in has expired or was already used. Sign in again."
)
LOCKED_STEP_MESSAGE: str = "Too many wrong codes. Sign in again."


def issue_mfa_challenge(
    mfa_challenge_repo: MfaChallengeRepoContract,
    wall_clock: WallClock[Microseconds],
    user_id: UserId,
    is_new_user: IsNewUser,
    client_ip_address: ClientIpAddress | None,
    requires_enrollment: bool,
) -> MfaChallengeView:
    now: Microseconds = wall_clock.now_unix()
    challenge = MfaChallengeDocument(
        user_id=user_id,
        expires_at=wall_clock.now_unix_with_delta(Seconds(int(MFA_CHALLENGE_LIFETIME))),
        is_new_user=is_new_user,
        requested_from_ip=client_ip_address,
        created_at=now,
        updated_at=now,
    )
    mfa_challenge_repo.save(challenge)
    return MfaChallengeView(
        mfa_challenge_id=challenge.id,
        expires_in_seconds=MFA_CHALLENGE_LIFETIME,
        requires_enrollment=requires_enrollment,
    )


def open_mfa_challenge(
    mfa_challenge_repo: MfaChallengeRepoContract,
    challenge_id: MfaChallengeId,
    now: Microseconds,
) -> MfaChallengeDocument:
    """
    The challenge while it may still be answered.

    Raises:
        AuthenticationRequiredError: unknown, used or expired.
        RateLimitedError: locked after too many wrong codes.
    """

    challenge: MfaChallengeDocument | None = mfa_challenge_repo.get(challenge_id)
    if challenge is None or challenge.is_consumed or now >= challenge.expires_at:
        raise AuthenticationRequiredError(EXPIRED_STEP_MESSAGE)

    if challenge.failed_attempts >= MFA_MAX_FAILED_ATTEMPTS:
        raise RateLimitedError(LOCKED_STEP_MESSAGE)

    return challenge


def take_mfa_attempt(
    mfa_challenge_repo: MfaChallengeRepoContract,
    challenge: MfaChallengeDocument,
    now: Microseconds,
) -> None:
    """
    Count this check before any code is compared, in one atomic step, so
    parallel guesses cannot all be compared.

    Raises:
        AuthenticationRequiredError: a parallel check used the challenge.
        RateLimitedError: no attempt is left.
    """

    attempt: MfaAttemptCount | None = mfa_challenge_repo.register_failed_attempt(
        challenge.id, MFA_MAX_FAILED_ATTEMPTS, now
    )
    if attempt is not None:
        if attempt >= MFA_MAX_FAILED_ATTEMPTS:
            logger.warning("Sign-in step %s took its last attempt.", challenge.id)
        return

    current: MfaChallengeDocument | None = mfa_challenge_repo.get(challenge.id)
    if current is None or current.is_consumed:
        raise AuthenticationRequiredError(EXPIRED_STEP_MESSAGE)

    raise RateLimitedError(LOCKED_STEP_MESSAGE)


def consume_mfa_challenge(
    mfa_challenge_repo: MfaChallengeRepoContract,
    challenge: MfaChallengeDocument,
    now: Microseconds,
) -> None:
    """
    Mark the challenge used (compare-and-swap): it opens one session only.

    Raises:
        AuthenticationRequiredError: a parallel check used it first.
    """

    if mfa_challenge_repo.consume(challenge.id, now) is None:
        raise AuthenticationRequiredError(EXPIRED_STEP_MESSAGE)
