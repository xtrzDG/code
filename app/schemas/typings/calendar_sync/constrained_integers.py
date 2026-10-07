"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class BusyBlockCount(BaseConstrainedTypedInt):
    """How many busy times one calendar source of a resource holds now."""

    ge = 0


class BusyEndsAtUnixSeconds(BaseConstrainedTypedInt):
    """
    UTC second at which a time made busy outside the platform (an event in a
    linked calendar, a reservation on Airbnb, a booking in a booking system)
    ends.

    Example:
        ends_at = BusyEndsAtUnixSeconds(1767272400)
    """

    ge = 0


class BusyStartsAtUnixSeconds(BaseConstrainedTypedInt):
    """UTC second at which a time made busy outside the platform starts."""

    ge = 0


class LinkedResourceCount(BaseConstrainedTypedInt):
    """How many resources of a business use an integration."""

    ge = 0


class LinkedSourceCount(BaseConstrainedTypedInt):
    """
    How many calendar sources (a Google calendar, imported feeds, a booking
    system) block one resource, or how many of them failed their last read.
    """

    ge = 0


# Keep abc order for all non example types, if possible.
