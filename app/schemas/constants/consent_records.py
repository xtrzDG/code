"""
The consent ledger (Codice privacy art. 130, GDPR art. 5(2) and 7(1)): for
what a consent was given, whether an entry gives or takes it back, and
where that happened.
"""

from enum import StrEnum


class ConsentPurpose(StrEnum):
    """What the customer agreed to: marketing messages (the campaigns)."""

    MARKETING = "marketing"


class ConsentEvent(StrEnum):
    """An entry gives the consent or takes it back."""

    GIVEN = "given"
    WITHDRAWN = "withdrawn"


class ConsentEventSource(StrEnum):
    """
    Where it happened: the box on the booking's page (/r/{token}), the team
    recording what the customer told them (the customer's card), the
    customer's STOP in a chat, or the erasure of the customer's data (which
    takes every consent back).
    """

    BOOKING_PAGE = "booking_page"
    IN_PERSON = "in_person"
    STOP = "stop"
    ERASURE = "erasure"
