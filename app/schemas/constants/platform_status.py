from enum import StrEnum


class StatusComponent(StrEnum):
    """
    The parts of the platform the public status page reports on: the
    website chat and hosted chat page (CHAT), WhatsApp, Instagram and
    Messenger (META), Telegram, phone calls (VOICE) and the owner cabinet
    with its sign-in (CABINET).
    """

    CHAT = "chat"
    META = "meta"
    TELEGRAM = "telegram"
    VOICE = "voice"
    CABINET = "cabinet"


class StatusLevel(StrEnum):
    """
    How a component works, from best to worst (STATUS_LEVEL_ORDER):
    normally, under planned maintenance, degraded (slow or partly failing)
    or down. NO_DATA is a day of the history nothing was recorded on.
    """

    OPERATIONAL = "operational"
    MAINTENANCE = "maintenance"
    DEGRADED = "degraded"
    OUTAGE = "outage"
    NO_DATA = "no_data"


# Worse levels sort later; NO_DATA never wins over a recorded level.
STATUS_LEVEL_ORDER: dict[StatusLevel, int] = {
    StatusLevel.NO_DATA: 0,
    StatusLevel.OPERATIONAL: 1,
    StatusLevel.MAINTENANCE: 2,
    StatusLevel.DEGRADED: 3,
    StatusLevel.OUTAGE: 4,
}


class AnnouncementLevel(StrEnum):
    """
    What a platform announcement says about the components it names: a
    notice only (INFO), planned maintenance, degraded service or an
    outage. The status page and the cabinet's banner take their colour
    and wording from it.
    """

    INFO = "info"
    MAINTENANCE = "maintenance"
    DEGRADED = "degraded"
    OUTAGE = "outage"


class AnnouncementStatus(StrEnum):
    """Whether an announcement is shown now or was resolved by the team."""

    ACTIVE = "active"
    RESOLVED = "resolved"
