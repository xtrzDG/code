"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DemoReplyPauseSeconds(BaseConstrainedTypedInt):
    """
    Seconds between a demo message and the one before it in its
    conversation (up to a day: a customer may come back the next morning).
    """

    ge = 0
    le = 86400


class LoadBookingCount(BaseConstrainedTypedInt):
    """Bookings a load-test dataset holds (`workshop seed-load --bookings`)."""

    ge = 0
    le = 50_000_000


class LoadBusinessCount(BaseConstrainedTypedInt):
    """Businesses a load-test dataset holds (`workshop seed-load --businesses`)."""

    ge = 1
    le = 100_000


class LoadBusinessIndex(BaseConstrainedTypedInt):
    """Position of one business in a load-test dataset, from 0."""

    ge = 0
    le = 100_000


class LoadMessageCount(BaseConstrainedTypedInt):
    """Messages a load-test dataset holds (`workshop seed-load --messages`)."""

    ge = 0
    le = 500_000_000


class LoadRandomSeed(BaseConstrainedTypedInt):
    """Seed of a load-test dataset: the same seed builds the same history."""

    ge = 0
    le = 2_147_483_647


class LoadVisitorCount(BaseConstrainedTypedInt):
    """
    Website-widget visitors with a conversation in a load-test dataset
    (`workshop seed-load --visitors`): the load test polls as them.
    """

    ge = 0
    le = 1_000_000
