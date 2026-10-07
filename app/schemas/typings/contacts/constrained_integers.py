"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ContactBookingCount(BaseConstrainedTypedInt):
    """Bookings of one customer (sandbox excluded)."""

    ge = 0


class ContactConversationCount(BaseConstrainedTypedInt):
    """Conversations of one customer across channels (sandbox excluded)."""

    ge = 0


class ContactLeadCount(BaseConstrainedTypedInt):
    """Leads (requests) of one customer (sandbox excluded)."""

    ge = 0


class ContactVisitCount(BaseConstrainedTypedInt):
    """
    Visits of one customer: their bookings that started already and were
    not cancelled, missed (no-show) or left unconfirmed.
    """

    ge = 0


class SegmentBookingCount(BaseConstrainedTypedInt):
    """A bound of a segment on how many bookings a customer made (sandbox excluded)."""

    ge = 0
    le = 10_000


class SegmentInactivityDays(BaseConstrainedTypedInt):
    """A segment's "last visit more than N days ago" (one day to ten years)."""

    ge = 1
    le = 3_650


class SegmentMemberCount(BaseConstrainedTypedInt):
    """How many customers a segment holds (as far as it was counted)."""

    ge = 0


# Keep abc order for all non example types, if possible.
