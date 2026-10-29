"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CircuitFailureCount(BaseConstrainedTypedInt):
    """Failures a circuit counted within its window (a closed circuit's)."""

    ge = 0
    le = 1000


class CircuitFailureThreshold(BaseConstrainedTypedInt):
    """Failures within the window that open a circuit."""

    ge = 1
    le = 1000


class CircuitOpenAgeSeconds(BaseConstrainedTypedInt):
    """Seconds since a circuit that is not closed opened."""

    ge = 0
    le = 1_000_000_000


class CircuitOpenSeconds(BaseConstrainedTypedInt):
    """Seconds an open circuit refuses calls before it lets one trial through."""

    ge = 1
    le = 3600


class CircuitWindowSeconds(BaseConstrainedTypedInt):
    """Seconds over which a circuit counts its recent failures."""

    ge = 1
    le = 3600


class CircuitWorkerCount(BaseConstrainedTypedInt):
    """Worker processes whose pulse reports a circuit (or reports it open)."""

    ge = 0
    le = 10_000


class ProviderSlotCount(BaseConstrainedTypedInt):
    """
    Sends one provider may have in flight at once in a worker process: its
    share of the outbound lane's threads.
    """

    ge = 1
    le = 64


# Keep abc order for all non example types, if possible.
