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


# Keep abc order for all non example types, if possible.
