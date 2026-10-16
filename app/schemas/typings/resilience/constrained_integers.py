"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CircuitFailureThreshold(BaseConstrainedTypedInt):
    """Failures within the window that open a circuit."""

    ge = 1
    le = 1000


class CircuitOpenSeconds(BaseConstrainedTypedInt):
    """Seconds an open circuit refuses calls before it lets one trial through."""

    ge = 1
    le = 3600


class CircuitWindowSeconds(BaseConstrainedTypedInt):
    """Seconds over which a circuit counts its recent failures."""

    ge = 1
    le = 3600


# Keep abc order for all non example types, if possible.
