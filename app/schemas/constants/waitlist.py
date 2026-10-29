from enum import StrEnum


class WaitlistStatus(StrEnum):
    """
    Where a customer's place on the waitlist stands.

    WAITING: nothing has opened up yet. OFFERED: a freed place is held for
    the customer until `offer_expires_at`. BOOKED: the customer said yes and
    the place became their booking. EXPIRED: the entry is over without a
    booking (`WaitlistEndReason` says why).
    """

    WAITING = "waiting"
    OFFERED = "offered"
    BOOKED = "booked"
    EXPIRED = "expired"


class WaitlistEndReason(StrEnum):
    """
    Why a waitlist entry ended without a booking: the customer said no to
    the place they were offered, did not answer within the hold, the day
    they wanted passed, they could be reached in no messenger or chat, or
    staff took them off the list.
    """

    DECLINED = "declined"
    NO_ANSWER = "no_answer"
    DATE_PASSED = "date_passed"
    UNREACHABLE = "unreachable"
    REMOVED = "removed"


class WaitlistAnswer(StrEnum):
    """A customer's whole reply to the place they were offered: yes or no."""

    YES = "yes"
    NO = "no"


class WaitlistListFilter(StrEnum):
    """Which entries the cabinet's waitlist shows: still open, booked, or ended."""

    ACTIVE = "active"
    BOOKED = "booked"
    ENDED = "ended"
