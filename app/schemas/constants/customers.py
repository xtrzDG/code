from enum import StrEnum


class CustomerTimelineKind(StrEnum):
    """What one entry of a customer's history is."""

    CONVERSATION = "conversation"
    BOOKING = "booking"
    LEAD = "lead"
    CALL = "call"


class CustomerStanding(StrEnum):
    """
    How well the business knows a customer, as the conversation header
    says it: NEW (first contact, no visit), RETURNING (wrote or called
    before, no visit yet), VISITED (one visit) or REGULAR (two visits or
    more). A visit is a booking that started already and was not
    cancelled, missed or left unconfirmed.
    """

    NEW = "new"
    RETURNING = "returning"
    VISITED = "visited"
    REGULAR = "regular"


class CustomerListFilter(StrEnum):
    """Which customers the list shows besides a tag: ALL, VIP or BLOCKED ones."""

    ALL = "all"
    VIP = "vip"
    BLOCKED = "blocked"
