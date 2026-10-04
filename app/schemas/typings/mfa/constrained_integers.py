"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class MfaAttemptCount(BaseConstrainedTypedInt):
    """Number of wrong authenticator or recovery codes entered for one challenge."""

    ge = 0
    le = 100


class MfaChallengeLifetimeSeconds(BaseConstrainedTypedInt):
    """How long the second step of a sign-in stays open, in seconds."""

    ge = 30
    le = 3600


class MemberWithoutTwoFactorCount(BaseConstrainedTypedInt):
    """How many members of a business have no authenticator set up."""

    ge = 0


class RecoveryCodeCount(BaseConstrainedTypedInt):
    """How many recovery codes a user has left (or gets in a new set)."""

    ge = 0
    le = 20


class StepUpMaxAgeSeconds(BaseConstrainedTypedInt):
    """
    How long after signing in or confirming their identity a person may do
    a sensitive action without confirming it again (STEP_UP_MAX_AGE_SECONDS).
    """

    ge = 60
    le = 86_400


class TotpTimeStep(BaseConstrainedTypedInt):
    """
    The 30-second step (Unix time // 30) an authenticator code belongs to;
    a factor remembers the last one used, so a code works only once.
    """

    ge = 0


# Keep abc order for all non example types, if possible.
