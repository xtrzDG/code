"""
Two-factor sign-in: a user's authenticator app, their recovery codes and
the second step of a sign-in (platform-wide collections, migration 1082).
"""

from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.mfa import TotpFactorStatus
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.mfa.booleans import IsMfaChallengeConsumed
from app.schemas.typings.mfa.constrained_integers import (
    MfaAttemptCount,
    TotpTimeStep,
)
from app.schemas.typings.mfa.prefixed_id import (
    MfaChallengeId,
    RecoveryCodeId,
    TotpFactorId,
)
from app.schemas.typings.mfa.strings import RecoveryCodeHash, SealedTotpSecret
from app.schemas.typings.users.booleans import IsNewUser
from app.schemas.typings.users.prefixed_id import UserId


class TotpFactorDocument(BaseDocument):
    """
    A user's authenticator app (RFC 6238: SHA-1, six digits, 30-second
    steps). The secret is stored sealed with the platform's key ring.

    A factor is PENDING from the moment its QR code is shown until the
    first code from the app confirms it, then ACTIVE; a user has at most
    one. `last_used_step` is the 30-second step of the last accepted code:
    a code is accepted only for a later step, so an overheard code cannot
    be used again.
    """

    id: TotpFactorId = Field(default_factory=TotpFactorId)
    user_id: UserId
    sealed_secret: SealedTotpSecret
    status: TotpFactorStatus = TotpFactorStatus.PENDING
    confirmed_at: Microseconds | None = None
    last_used_step: TotpTimeStep | None = None
    last_used_at: Microseconds | None = None


class RecoveryCodeDocument(BaseDocument):
    """
    One single-use recovery code of a user with an authenticator, for the
    day the phone with the app is lost. Only a keyed hash is stored; a code
    is spent (`used_at`) by compare-and-swap, so it opens one sign-in only.
    """

    id: RecoveryCodeId = Field(default_factory=RecoveryCodeId)
    user_id: UserId
    code_hash: RecoveryCodeHash
    used_at: Microseconds | None = None


class MfaChallengeDocument(BaseDocument):
    """
    The second step of one sign-in. It is issued once the login code
    matched, for a user with an authenticator and for every platform admin
    (who sets one up here when they have none), and opens the session
    when a code of the app or a recovery code matches.

    It lives five minutes, five wrong codes lock it, and it is consumed by
    compare-and-swap, so it opens one session only. `is_new_user` is what
    the login code step found, for the cabinet's welcome.
    """

    id: MfaChallengeId = Field(default_factory=MfaChallengeId)
    user_id: UserId
    expires_at: Microseconds
    failed_attempts: MfaAttemptCount = MfaAttemptCount(0)
    is_consumed: IsMfaChallengeConsumed = False
    is_new_user: IsNewUser = False
    requested_from_ip: ClientIpAddress | None = None
