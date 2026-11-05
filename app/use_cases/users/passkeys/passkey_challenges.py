"""The challenge of one passkey ceremony: issuing it, and taking it once."""

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
)
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.domain.passkeys import PasskeyChallengeDocument
from app.schemas.typings.mfa.prefixed_id import MfaChallengeId
from app.schemas.typings.passkeys.prefixed_id import PasskeyChallengeId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.passkey_policy import passkey_rejected

PASSKEY_CHALLENGE_LIFETIME: Seconds = Seconds(5 * 60)
EXPIRED_CEREMONY_MESSAGE: str = (
    "This passkey request has expired or was already answered. Try again."
)


def issue_passkey_challenge(
    challenge_repo: PasskeyChallengeRepoContract,
    ceremony: PasskeyCeremonyAdapterContract,
    wall_clock: WallClock[Microseconds],
    user_id: UserId,
    purpose: PasskeyCeremonyPurpose,
    mfa_challenge_id: MfaChallengeId | None = None,
) -> PasskeyChallengeDocument:
    """A new random challenge for one ceremony of this person (five minutes)."""

    now: Microseconds = wall_clock.now_unix()
    challenge = PasskeyChallengeDocument(
        user_id=user_id,
        purpose=purpose,
        challenge=ceremony.new_challenge(),
        mfa_challenge_id=mfa_challenge_id,
        expires_at=wall_clock.now_unix_with_delta(PASSKEY_CHALLENGE_LIFETIME),
        created_at=now,
        updated_at=now,
    )
    challenge_repo.save(challenge)
    return challenge


def take_passkey_challenge(
    challenge_repo: PasskeyChallengeRepoContract,
    challenge_id: PasskeyChallengeId,
    user_id: UserId,
    purpose: PasskeyCeremonyPurpose,
    now: Microseconds,
    mfa_challenge_id: MfaChallengeId | None = None,
) -> PasskeyChallengeDocument:
    """
    The challenge, consumed by compare-and-swap before the answer is
    checked: whatever the check says, the challenge never counts again.
    It must be this person's, for this purpose (and this sign-in step),
    and not expired.

    Raises:
        PasskeyRejectedError: unknown, someone else's, another purpose,
            expired, or already taken (by a parallel answer too).
    """

    challenge: PasskeyChallengeDocument | None = challenge_repo.get(challenge_id)
    if (
        challenge is None
        or challenge.user_id != user_id
        or challenge.purpose is not purpose
        or challenge.mfa_challenge_id != mfa_challenge_id
        or now >= challenge.expires_at
    ):
        raise passkey_rejected(EXPIRED_CEREMONY_MESSAGE)

    taken: PasskeyChallengeDocument | None = challenge_repo.consume(challenge_id, now)
    if taken is None:
        raise passkey_rejected(EXPIRED_CEREMONY_MESSAGE)

    return taken
