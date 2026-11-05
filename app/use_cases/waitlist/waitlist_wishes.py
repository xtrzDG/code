"""
What a customer joining the waitlist wants, made exact: the service and the
resource they named (by id or by a name in any script), a time window in
order, the moment their wish is over, and the free times that already fit
it (then they need no waitlist).
"""

from collections.abc import Sequence
from datetime import date, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import AvailabilityResult, AvailableSlot
from app.schemas.dto.growth.waitlist_joining import JoinWaitlistCommand
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.utilities.bookings.target_resolution import resolve_resource, resolve_service
from app.utilities.scheduling.zoned_time import (
    lenient_utc_seconds,
    parse_local_date,
    parse_time_of_day,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
MINUTES_PER_DAY: int = 24 * 60
# Free times named back to the model when the wish needs no waitlist.
MAX_NAMED_TIMES: int = 5


class WaitlistWish(NamedTuple):
    """The resolved service and resource of a wish (None: any)."""

    service: KnowledgeItemDocument | None
    resource: ResourceDocument | None


def resolve_wish(
    command: JoinWaitlistCommand,
    items: Sequence[KnowledgeItemDocument],
    resources: Sequence[ResourceDocument],
) -> WaitlistWish:
    """
    Raises:
        ValidationFailedError: an unknown or ambiguous service or resource,
            or a time window that ends before it starts.
    """

    if (
        command.time_from is not None
        and command.time_to is not None
        and parse_time_of_day(command.time_to) < parse_time_of_day(command.time_from)
    ):
        raise ValidationFailedError(
            "The time window ends before it starts; ask the customer again."
        )

    return WaitlistWish(
        service=(
            None
            if command.service_reference is None
            else resolve_service(command.service_reference, items)
        ),
        resource=(
            None
            if command.resource_reference is None
            else resolve_resource(command.resource_reference, resources)
        ),
    )


def wish_ends_at(command: JoinWaitlistCommand, zone: ZoneInfo) -> Microseconds:
    """The end of the window on the wanted day (the day's end without one), UTC."""

    local_date: date = parse_local_date(command.date)
    if command.time_to is None:
        seconds: int = lenient_utc_seconds(local_date + timedelta(days=1), 0, zone)
    else:
        seconds = lenient_utc_seconds(
            local_date, parse_time_of_day(command.time_to), zone
        )

    return Microseconds(seconds * MICROSECONDS_PER_SECOND)


def fitting_free_times(
    result: AvailabilityResult, command: JoinWaitlistCommand
) -> list[AvailableSlot]:
    """The free times (or stays) of the day that already fit the window."""

    return [
        slot
        for slot in result.slots
        if slot.date == command.date and is_in_window(slot.time, command)
    ]


def is_in_window(time: LocalTimeOfDay | None, command: JoinWaitlistCommand) -> bool:
    if time is None:
        return True

    minute: int = parse_time_of_day(time)
    lower: int = (
        0 if command.time_from is None else parse_time_of_day(command.time_from)
    )
    upper: int = (
        MINUTES_PER_DAY
        if command.time_to is None
        else parse_time_of_day(command.time_to)
    )
    return lower <= minute <= upper


def refuse_free_times(free: Sequence[AvailableSlot]) -> ValidationFailedError:
    """The wish fits free times: the model should offer them instead."""

    times: list[str] = [
        f"{slot.date} {slot.time}" if slot.time is not None else str(slot.date)
        for slot in free[:MAX_NAMED_TIMES]
    ]
    return ValidationFailedError(
        "There is free time that fits the customer's wish: "
        + ", ".join(times)
        + ". Offer it with create_booking instead of the waitlist."
    )
