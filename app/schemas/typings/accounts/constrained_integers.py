"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class OtpAttemptCount(BaseConstrainedTypedInt):
    """Number of wrong codes entered for one challenge."""

    ge = 0
    le = 100


class OtpLifetimeSeconds(BaseConstrainedTypedInt):
    """How long a one-time login code stays valid, in seconds."""

    ge = 30
    le = 3600


class SessionLifetimeSeconds(BaseConstrainedTypedInt):
    """How long an owner session stays valid, in seconds."""

    ge = 60


# Keep abc order for all non example types, if possible.
