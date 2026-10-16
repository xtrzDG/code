from enum import StrEnum


class HelpTopic(StrEnum):
    """
    The groups of the help center: getting started, connecting the
    channels customers write and call in, the daily work (inbox, bookings,
    teaching the assistant), and the account (billing, privacy).
    """

    GETTING_STARTED = "getting_started"
    CHANNELS = "channels"
    DAILY_WORK = "daily_work"
    ACCOUNT = "account"
