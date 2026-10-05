from enum import StrEnum


class RebookingRuleKind(StrEnum):
    """
    What a business's rebooking campaign sends, and when:

    - REBOOK: an invitation back the given days after a customer's last
      visit (a salon after five weeks);
    - RECALL: a reminder that a regular check is due the given days after
      the last visit (a clinic, a car service);
    - PRE_ARRIVAL: a note with the practical details the given days before
      a booking starts (a hotel two days before arrival).
    """

    REBOOK = "rebook"
    RECALL = "recall"
    PRE_ARRIVAL = "pre_arrival"


class CampaignAudience(StrEnum):
    """
    Who a campaign may write to: every customer the rule finds, or only the
    members of one of the owner's saved segments (Customers → Segments).
    """

    ALL_CUSTOMERS = "all_customers"
    SEGMENT = "segment"


class CampaignMessageStatus(StrEnum):
    """
    SENT went into the outbox; BOOKED is a sent invitation the customer
    booked again after (within the attribution window); SKIPPED was never
    sent (`CampaignSkipReason`).
    """

    SENT = "sent"
    BOOKED = "booked"
    SKIPPED = "skipped"


class CampaignSkipReason(StrEnum):
    """
    Why a customer the rule found got no message: they said STOP (or are on
    the suppression list, or blocked), are unknown or erased, can be reached
    in no connected messenger, or only where the 24-hour window is closed
    without an approved template.
    """

    OPTED_OUT = "opted_out"
    NO_CONTACT = "no_contact"
    NO_CHANNEL = "no_channel"
    WINDOW_CLOSED = "window_closed"
