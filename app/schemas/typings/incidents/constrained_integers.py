"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AffectedBusinessCount(BaseConstrainedTypedInt):
    """
    How many businesses an incident reached: those it names, or for an
    all-businesses incident those the worker's walk has reached so far.
    """

    ge = 0


class AffectedRecordCount(BaseConstrainedTypedInt):
    """
    About how many records (messages, contacts, bookings, recordings) a
    data breach concerns, as far as known (DPA section 12.1).
    """

    ge = 0
    le = 1_000_000_000


class AffectedSubjectCount(BaseConstrainedTypedInt):
    """
    About how many people (customers, staff) a data breach concerns, as far
    as known (DPA section 12.1).
    """

    ge = 0
    le = 1_000_000_000


class NotifiedOwnerCount(BaseConstrainedTypedInt):
    """How many owner notices an incident queued in the outbox."""

    ge = 0


# Keep abc order for all non example types, if possible.
