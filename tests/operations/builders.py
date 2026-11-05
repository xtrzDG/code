"""Small value builders for operations tests: hours, minutes and managers."""

from datetime import datetime

from app.schemas.constants.businesses import Weekday
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag

# Monday 2026-10-05 08:00 UTC = 12:00 in Tbilisi.
DEFAULT_NOW: datetime = datetime.fromisoformat("2026-10-05T08:00:00+00:00")
ALL_WEEKDAYS: tuple[Weekday, ...] = tuple(Weekday)


def minute(text: str) -> int:
    hours, minutes = text.split(":")
    return int(hours) * 60 + int(minutes)


def interval(weekday: Weekday, opens: str, closes: str) -> OpeningInterval:
    closes_minute: int = minute(closes) or 24 * 60
    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(minute(opens)),
        closes_at=ClosingMinuteOfDay(closes_minute),
    )


def every_day(opens: str, closes: str) -> list[OpeningInterval]:
    return [interval(weekday, opens, closes) for weekday in ALL_WEEKDAYS]


def manager(
    name: str,
    channel: ManagerContactChannel,
    address: str,
    language: str,
) -> ManagerContact:
    return ManagerContact(
        name=ManagerName(name),
        channel=channel,
        address=ManagerContactAddress(address),
        language=LanguageTag(language),
    )


DEFAULT_MANAGERS: tuple[ManagerContact, ...] = (
    manager("Nino", ManagerContactChannel.TELEGRAM, "4242", "ka"),
    manager("Daniel", ManagerContactChannel.WHATSAPP, "+995555000111", "ru"),
    manager("Anna", ManagerContactChannel.EMAIL, "anna@example.com", "en"),
)


def seconds(text: str) -> int:
    """Unix seconds of an ISO datetime with an offset."""

    return int(datetime.fromisoformat(text).timestamp())
