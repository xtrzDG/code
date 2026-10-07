from enum import StrEnum


class CalendarConnectionFailure(StrEnum):
    """
    Why connecting a calendar did not finish; the owner is sent back to the
    cabinet with this reason.
    """

    ACCESS_DENIED = "access_denied"
    LINK_EXPIRED = "link_expired"
    NO_OFFLINE_ACCESS = "no_offline_access"
    PROVIDER_ERROR = "provider_error"
