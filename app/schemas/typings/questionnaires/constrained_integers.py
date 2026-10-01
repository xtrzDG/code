"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ResourceCapacity(BaseConstrainedTypedInt):
    """How many people one bookable resource serves at once."""

    ge = 1
    le = 10000


class ResourceUnitCount(BaseConstrainedTypedInt):
    """How many identical units of a bookable resource exist."""

    ge = 1
    le = 1000


class SlotDurationMinutes(BaseConstrainedTypedInt):
    """Default length of one booking of a resource, in minutes (up to 30 days)."""

    ge = 5
    le = 43200


# Keep abc order for all non example types, if possible.
