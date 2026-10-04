"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class BufferMinutes(BaseConstrainedTypedInt):
    """
    Minutes a performer or room stays blocked after a service (cleaning,
    preparation, rest), so the next booking cannot start right away.
    """

    ge = 0
    le = 240


class KnowledgeSearchLimit(BaseConstrainedTypedInt):
    """How many knowledge items a search returns (concept: up to 5)."""

    ge = 1
    le = 20


class NightlyRateMinor(BaseConstrainedTypedInt):
    """
    Price of one night of a room type in a season, in minor units of the
    item's currency (a stay costs the sum of its nights).
    """

    ge = 0


class ServiceDurationMinutes(BaseConstrainedTypedInt):
    """
    How long a service, a package or a visit takes, in minutes (5 minutes
    to 12 hours): a booking of it lasts this long.
    """

    ge = 5
    le = 720


# Keep abc order for all non example types, if possible.
