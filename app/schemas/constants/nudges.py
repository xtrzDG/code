"""Activation nudges: reminders that bring an owner back to an unfinished launch."""

from enum import StrEnum


class NudgeCode(StrEnum):
    """
    One activation nudge, sent at most once per business:

    - NOT_LIVE_DAY_1, NOT_LIVE_DAY_3, NOT_LIVE_DAY_7: days after the
      business was created, while its assistant has not gone live;
    - LIVE_DAY_2, LIVE_DAY_5: days after going live, while the business
      has a single channel where customers write or no real conversation;
    - LIVE_DAY_10: days after going live, while nobody opened the hosted
      chat page and the QR code was never printed or saved.
    """

    NOT_LIVE_DAY_1 = "not_live_day_1"
    NOT_LIVE_DAY_3 = "not_live_day_3"
    NOT_LIVE_DAY_7 = "not_live_day_7"
    LIVE_DAY_2 = "live_day_2"
    LIVE_DAY_5 = "live_day_5"
    LIVE_DAY_10 = "live_day_10"


class NudgeAnchor(StrEnum):
    """
    What a nudge's days count from: the business's CREATION (the launch is
    not done) or its GO_LIVE (the first customers are not there yet).
    """

    CREATION = "creation"
    GO_LIVE = "go_live"


class NudgeTopic(StrEnum):
    """
    What a nudge asks the owner to do, which picks its text and link:
    FINISH_SETUP (the tunnel, at the saved step), DONE_FOR_YOU (finish it,
    or let the platform team set it up), CONNECT_CHANNEL (WhatsApp,
    Telegram and the rest), SHARE_LINK (the link and QR code where
    customers see them) and PRINT_QR (the table and counter card).
    """

    FINISH_SETUP = "finish_setup"
    DONE_FOR_YOU = "done_for_you"
    CONNECT_CHANNEL = "connect_channel"
    SHARE_LINK = "share_link"
    PRINT_QR = "print_qr"
