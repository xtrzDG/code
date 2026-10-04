"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class BookingDurationMinutes(BaseConstrainedTypedInt):
    """Length of one time-slot booking in minutes (up to 30 days)."""

    ge = 5
    le = 43200


class BookingEndsAtUnixSeconds(BaseConstrainedTypedInt):
    """UTC UNIX timestamp (seconds) when a booking ends."""

    ge = 0


class BookingReminderLeadSeconds(BaseConstrainedTypedInt):
    """How long before a booking starts its reminder is sent (1 min to 7 days)."""

    ge = 60
    le = 604800


class BookingSearchBoundSeconds(BaseConstrainedTypedInt):
    """
    UTC UNIX timestamp (seconds) that bounds the bookings a query reads
    (the start of a local day, or now for the ones not over yet).
    """

    ge = 0


class BookingStartsAtUnixSeconds(BaseConstrainedTypedInt):
    """UTC UNIX timestamp (seconds) when a booking starts."""

    ge = 0


class BookingValueMinor(BaseConstrainedTypedInt):
    """
    What one booking is worth, in minor units of its currency: the price
    of the booked service, or the nightly rates of a stay's nights.
    """

    ge = 0


class CalendarTokenLifetimeSeconds(BaseConstrainedTypedInt):
    """Seconds an OAuth access token of a connected calendar stays valid."""

    ge = 0


class MinNoticeMinutes(BaseConstrainedTypedInt):
    """How long before the start a booking must be made (concept min_notice)."""

    ge = 0
    le = 525600


class NightCount(BaseConstrainedTypedInt):
    """Number of nights of a hotel or rental booking."""

    ge = 1
    le = 365


class PartySize(BaseConstrainedTypedInt):
    """Number of people in a booking or a group request."""

    ge = 1
    le = 10000


class ResourceCapacity(BaseConstrainedTypedInt):
    """How many people one unit of a resource serves at once."""

    ge = 1
    le = 10000


class ResourceUnitCount(BaseConstrainedTypedInt):
    """How many identical units of a resource exist (rooms of one type)."""

    ge = 1
    le = 1000


class SlotDurationMinutes(BaseConstrainedTypedInt):
    """Default booking length of a resource, in minutes (concept slot_minutes)."""

    ge = 5
    le = 43200


# Keep abc order for all non example types, if possible.
