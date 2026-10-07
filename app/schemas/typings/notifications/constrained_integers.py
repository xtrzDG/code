"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class PushTimeToLiveSeconds(BaseConstrainedTypedInt):
    """
    How long a push service keeps a notification for a device that is
    offline, in seconds (RFC 8030 TTL; at most four weeks).

    Example:
        ttl = PushTimeToLiveSeconds(86_400)
    """

    ge = 0
    le = 2_419_200


# Keep abc order for all non example types, if possible.
