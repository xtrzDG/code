"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class BusyTimeFetchSeconds(BaseConstrainedTypedFloat):
    """
    How long one read of a resource's busy times from outside (Google
    free/busy, an iCal feed, a booking system) may take, in seconds: 2 s
    when a person or a customer waits for it, longer in the background.

    Example:
        timeout = BusyTimeFetchSeconds(2.0)
    """

    gt = 0.0
    le = 30.0


# Keep abc order for all non example types, if possible.
