"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class BookingDurationMinutes(BaseConstrainedTypedInt):
    """Length of one booking in minutes (up to 30 days)."""

    ge = 5
    le = 43200


class BookingEndsAtUnixSeconds(BaseConstrainedTypedInt):
    """UTC UNIX timestamp (seconds) when a booking ends."""

    ge = 0


class BookingStartsAtUnixSeconds(BaseConstrainedTypedInt):
    """UTC UNIX timestamp (seconds) when a booking starts."""

    ge = 0


class PartySize(BaseConstrainedTypedInt):
    """Number of people in a booking or a group request."""

    ge = 1
    le = 10000


# Keep abc order for all non example types, if possible.
