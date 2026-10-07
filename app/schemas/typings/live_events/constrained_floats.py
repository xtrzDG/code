"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class LiveStreamHeartbeatSeconds(BaseConstrainedTypedFloat):
    """
    How long a quiet live stream waits before it sends a heartbeat comment,
    so proxies keep the connection open and a closed tab is noticed.

    Example:
        heartbeat = LiveStreamHeartbeatSeconds(20.0)
    """

    gt = 0.0
    le = 300.0


class LiveStreamLifetimeSeconds(BaseConstrainedTypedFloat):
    """
    How long one live stream stays open before the server ends it; the
    cabinet reconnects at once, which checks the session and the person's
    access again and spreads streams over the API instances.

    Example:
        lifetime = LiveStreamLifetimeSeconds(900.0)
    """

    gt = 0.0
    le = 86_400.0


# Keep abc order for all non example types, if possible.
