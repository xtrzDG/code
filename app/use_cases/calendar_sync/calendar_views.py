"""A resource's calendars as the cabinet shows them (no secret ever leaves)."""

from collections.abc import Sequence
from typing import NamedTuple

from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import BookingSystemKind, BusyTimeSource
from app.schemas.domain.calendar_sync import (
    BusySourceStatus,
    CalendarBusyTimesDocument,
    IcalExportFeedDocument,
    ResourceCalendarLinkDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.resource_calendar import (
    BookingSystemView,
    BusySourceStatusView,
    BusyTimeView,
    GoogleCalendarSourceView,
    IcalExportView,
    IcalImportView,
    ResourceCalendarView,
)
from app.schemas.typings.calendar_sync.constrained_strings import CalendarFeedHost

MICROSECONDS_PER_SECOND: int = 1_000_000
UPCOMING_LIMIT: int = 20


class CalendarViewParts(NamedTuple):
    """What a view needs besides the resource and its settings."""

    is_google_available: bool
    is_google_connected: bool
    booking_system_kinds: list[BookingSystemKind]
    busy_times: Sequence[CalendarBusyTimesDocument]
    export_feed: IcalExportFeedDocument | None
    now: Microseconds


def build_calendar_view(
    resource: ResourceDocument,
    link: ResourceCalendarLinkDocument | None,
    parts: CalendarViewParts,
) -> ResourceCalendarView:
    return ResourceCalendarView(
        business_id=resource.business_id,
        resource_id=resource.id,
        resource_name=resource.name,
        google=GoogleCalendarSourceView(
            is_available=parts.is_google_available,
            is_connected=parts.is_google_connected,
            calendar_id=resource.external_calendar_id,
            status=(
                None
                if link is None or link.google_status is None
                else status_view(link.google_status)
            ),
        ),
        ical_imports=[]
        if link is None
        else [
            IcalImportView(
                feed_id=feed.feed_id,
                host=feed.host,
                added_at=feed.added_at,
                status=status_view(feed.status),
            )
            for feed in link.ical_imports
        ],
        ical_export=IcalExportView(
            is_on=link is not None and link.ical_export_token_hash is not None,
            created_at=None if link is None else link.ical_export_created_at,
            last_read_at=(
                None if parts.export_feed is None else parts.export_feed.last_read_at
            ),
        ),
        booking_system=(
            None
            if link is None or link.booking_system is None
            else BookingSystemView(
                kind=link.booking_system.kind,
                external_resource_id=link.booking_system.external_resource_id,
                external_resource_title=link.booking_system.external_resource_title,
                added_at=link.booking_system.added_at,
                status=status_view(link.booking_system.status),
            )
        ),
        booking_system_kinds=parts.booking_system_kinds,
        next_sync_at=None if link is None else link.next_sync_at,
        upcoming_busy_times=upcoming_busy_times(resource, link, parts),
    )


def status_view(status: BusySourceStatus) -> BusySourceStatusView:
    return BusySourceStatusView(
        last_attempt_at=status.last_attempt_at,
        last_synced_at=status.last_synced_at,
        block_count=status.block_count,
        problem=status.problem,
        problem_detail=status.problem_detail,
    )


def upcoming_busy_times(
    resource: ResourceDocument,
    link: ResourceCalendarLinkDocument | None,
    parts: CalendarViewParts,
) -> list[BusyTimeView]:
    """The next busy times of the resource's sources that are still linked."""

    hosts: dict[str, CalendarFeedHost] = (
        {}
        if link is None
        else {str(feed.feed_id): feed.host for feed in link.ical_imports}
    )
    now_seconds: int = int(parts.now) // MICROSECONDS_PER_SECOND
    views: list[BusyTimeView] = [
        BusyTimeView(
            source=document.source,
            feed_host=hosts.get(str(document.feed_id)),
            starts_at=block.starts_at,
            ends_at=block.ends_at,
        )
        for document in parts.busy_times
        if document.resource_id == resource.id and is_linked(document, link, resource)
        for block in document.blocks
        if int(block.ends_at) > now_seconds
    ]
    return sorted(views, key=lambda view: int(view.starts_at))[:UPCOMING_LIMIT]


def is_linked(
    document: CalendarBusyTimesDocument,
    link: ResourceCalendarLinkDocument | None,
    resource: ResourceDocument,
) -> bool:
    if link is None:
        return False
    if document.source is BusyTimeSource.GOOGLE:
        return resource.external_calendar_id is not None
    if document.source is BusyTimeSource.BOOKING_SYSTEM:
        return link.booking_system is not None
    return any(feed.feed_id == document.feed_id for feed in link.ical_imports)
