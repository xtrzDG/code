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


class OtpSendLimit(BaseConstrainedTypedInt):
    """
    How many login codes may be sent in an hour (per destination, per
    client address, or in total).
    """

    ge = 1
    le = 1_000_000


class OtpVerifyLimit(BaseConstrainedTypedInt):
    """
    How many login code checks one client address may make in ten minutes.
    """

    ge = 1
    le = 1_000_000


class SessionLifetimeSeconds(BaseConstrainedTypedInt):
    """How long a session stays valid, in seconds."""

    ge = 60


# Keep abc order for all non example types, if possible.
