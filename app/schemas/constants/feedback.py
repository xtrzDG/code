from enum import StrEnum


class FeedbackRequestStatus(StrEnum):
    """
    Where the request for feedback after one visit stands.

    SENT went into the outbox and waits for the customer's rating;
    ANSWERED got one; SKIPPED was never sent (`FeedbackSkipReason`);
    FAILED was given up by the outbox (the platform refused it, or every
    retry failed).
    """

    SENT = "sent"
    ANSWERED = "answered"
    SKIPPED = "skipped"
    FAILED = "failed"


class FeedbackSkipReason(StrEnum):
    """
    Why a visit was not asked about: the customer opted out of messages
    they did not ask for, is unknown or erased, can be reached in no
    connected messenger, can be reached only where the 24-hour window is
    closed and no approved template is named, was already asked today
    about another visit, or a daily cap was reached.
    """

    OPTED_OUT = "opted_out"
    NO_CONTACT = "no_contact"
    NO_CHANNEL = "no_channel"
    WINDOW_CLOSED = "window_closed"
    ALREADY_ASKED = "already_asked"
    DAILY_LIMIT = "daily_limit"


class CustomerSignalKind(StrEnum):
    """
    A message the platform answers itself instead of the assistant: the
    customer opts out of (STOP) or back into (START) messages they did
    not ask for, rates their visit, or answers a waitlist offer.
    """

    OPT_OUT = "opt_out"
    OPT_IN = "opt_in"
    VISIT_SCORE = "visit_score"
    # A yes or no to a place freed for them on the waitlist (never stored).
    WAITLIST_ANSWER = "waitlist_answer"
