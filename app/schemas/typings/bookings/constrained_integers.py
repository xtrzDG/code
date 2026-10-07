"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class BookedUnitCount(BaseConstrainedTypedInt):
    """How many units of a place booked by the night (rooms) are taken one night."""

    ge = 0
    le = 1000


class BookedUnitMinutes(BaseConstrainedTypedInt):
    """
    Minutes the bookings of a place take within its opening hours of one
    day, summed over its units (two tables for an hour: 120).
    """

    ge = 0


class BookingDurationMinutes(BaseConstrainedTypedInt):
    """Length of one time-slot booking in minutes (up to 30 days)."""

    ge = 5
    le = 43200


class BookingEndsAtUnixSeconds(BaseConstrainedTypedInt):
    """UTC UNIX timestamp (seconds) when a booking ends."""

    ge = 0


class BookingGridDayCount(BaseConstrainedTypedInt):
    """How many local days one bookings calendar shows (a day up to a month)."""

    ge = 1
    le = 31


class BookingGridReadCeiling(BaseConstrainedTypedInt):
    """
    The most bookings one calendar window reads before it stops and says
    so (a guard against a runaway window, far above a busy month).
    """

    ge = 1
    le = 20000


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


class GridBookingCount(BaseConstrainedTypedInt):
    """How many bookings (not cancelled) a place has on one day of the calendar."""

    ge = 0


class MinNoticeMinutes(BaseConstrainedTypedInt):
    """How long before the start a booking must be made (concept min_notice)."""

    ge = 0
    le = 525600


class NightCount(BaseConstrainedTypedInt):
    """Number of nights of a hotel or rental booking."""

    ge = 1
    le = 365


class OpenUnitCount(BaseConstrainedTypedInt):
    """How many units of a place booked by the night (rooms) can be sold one night."""

    ge = 0
    le = 1000


class OpenUnitMinutes(BaseConstrainedTypedInt):
    """
    Minutes a place is open on one day, summed over its units (three
    tables open ten hours: 1800): what its bookings could fill.
    """

    ge = 0


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
