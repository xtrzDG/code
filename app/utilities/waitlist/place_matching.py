"""
Whether a freed place fits what a waiting customer asked for: the day,
their time window, the party (the resource must seat it), a stay's
nights, the kind of resource, a named master or room, and a service.
"""

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.utilities.scheduling.zoned_time import (
    minute_of_day,
    parse_local_date,
    parse_time_of_day,
    to_local_moment,
)

SECONDS_PER_DAY: int = 24 * 60 * 60


@dataclass(frozen=True)
class FreedPlaceFacts:
    """A freed place as a wish is compared with it, in the business's time."""

    resource: ResourceDocument
    local_date: date
    minute_of_day: int | None
    nights: int | None
    service_item_id: KnowledgeItemId | None


def describe_freed_place(
    place: FreedPlace,
    resource: ResourceDocument,
    freed: BookingDocument,
    zone: ZoneInfo,
) -> FreedPlaceFacts:
    """The local day, time (time slots) or nights (stays) and the service."""

    starts: datetime = to_local_moment(int(place.starts_at), zone)
    is_stay: bool = resource.booking_unit is BookingUnit.NIGHT
    ends: datetime = to_local_moment(int(place.ends_at), zone)
    return FreedPlaceFacts(
        resource=resource,
        local_date=starts.date(),
        minute_of_day=None if is_stay else minute_of_day(starts),
        nights=max((ends.date() - starts.date()).days, 1) if is_stay else None,
        service_item_id=freed.service_item_id,
    )


def entry_fits(entry: WaitlistEntryDocument, facts: FreedPlaceFacts) -> bool:
    """The freed place is what the waiting customer asked for."""

    if entry.is_sandbox or parse_local_date(entry.date) != facts.local_date:
        return False

    if entry.resource_id is not None and entry.resource_id != facts.resource.id:
        return False

    if entry.resource_kind is not None and entry.resource_kind is not (
        facts.resource.kind
    ):
        return False

    if int(entry.party_size) > int(facts.resource.capacity):
        return False

    if (
        entry.service_item_id is not None
        and entry.service_item_id != facts.service_item_id
    ):
        return False

    if facts.nights is not None:
        return int(entry.nights or 1) == facts.nights

    return is_within_window(entry, facts.minute_of_day)


def is_within_window(entry: WaitlistEntryDocument, minute: int | None) -> bool:
    """The place starts within the customer's time window (none: any time)."""

    if minute is None:
        return True

    if entry.time_from is not None and minute < parse_time_of_day(entry.time_from):
        return False

    return entry.time_to is None or minute <= parse_time_of_day(entry.time_to)
