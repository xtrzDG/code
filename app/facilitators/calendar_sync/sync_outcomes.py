"""
How one read of a source went, and how the reads of a sync are recorded on
the resource's calendar settings as stored at that moment (a source
unlinked meanwhile is not brought back).
"""

from typing import NamedTuple

from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import BusyTimeSource, CalendarSyncProblem
from app.schemas.domain.calendar_sync import (
    BusySourceStatus,
    ResourceCalendarLinkDocument,
)
from app.schemas.typings.bookings.constrained_strings import CalendarSyncErrorSummary
from app.schemas.typings.calendar_sync.constrained_integers import BusyBlockCount
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.utilities.calendar_sync.busy_windows import SYNC_INTERVAL_SECONDS

MICROSECONDS_PER_SECOND: int = 1_000_000
MAX_DETAIL_LENGTH: int = 300


class SourceOutcome(NamedTuple):
    """The read of one source (one feed for iCal) and its new status."""

    source: BusyTimeSource
    feed_id: IcalImportFeedId | None
    status: BusySourceStatus


def succeeded(at: Microseconds, block_count: int) -> BusySourceStatus:
    return BusySourceStatus(
        last_attempt_at=at,
        last_synced_at=at,
        block_count=BusyBlockCount(block_count),
    )


def failed(
    previous: BusySourceStatus | None,
    at: Microseconds,
    problem: CalendarSyncProblem,
    detail: str,
) -> BusySourceStatus:
    """The failure, keeping when the source last synced and what it brought."""

    text: str = " ".join(detail.split())[:MAX_DETAIL_LENGTH] or problem.value
    return BusySourceStatus(
        last_attempt_at=at,
        last_synced_at=None if previous is None else previous.last_synced_at,
        block_count=BusyBlockCount(0) if previous is None else previous.block_count,
        problem=problem,
        problem_detail=CalendarSyncErrorSummary(text),
    )


def has_sources(link: ResourceCalendarLinkDocument) -> bool:
    return (
        link.google_status is not None
        or bool(link.ical_imports)
        or link.booking_system is not None
    )


def is_still_linked(link: ResourceCalendarLinkDocument, outcome: SourceOutcome) -> bool:
    if outcome.source is BusyTimeSource.GOOGLE:
        return link.google_status is not None
    if outcome.source is BusyTimeSource.BOOKING_SYSTEM:
        return link.booking_system is not None
    return any(feed.feed_id == outcome.feed_id for feed in link.ical_imports)


def record_outcomes(
    link: ResourceCalendarLinkDocument,
    outcomes: list[SourceOutcome],
    now: Microseconds,
) -> ResourceCalendarLinkDocument:
    """The stored settings with each still-linked source's new status."""

    for outcome in outcomes:
        if not is_still_linked(link, outcome):
            continue
        if outcome.source is BusyTimeSource.GOOGLE:
            link.google_status = outcome.status
        elif outcome.source is BusyTimeSource.BOOKING_SYSTEM and link.booking_system:
            link.booking_system.status = outcome.status
        else:
            for feed in link.ical_imports:
                if feed.feed_id == outcome.feed_id:
                    feed.status = outcome.status

    link.next_sync_at = (
        Microseconds(int(now) + SYNC_INTERVAL_SECONDS * MICROSECONDS_PER_SECOND)
        if has_sources(link)
        else None
    )
    link.updated_at = now
    return link


def previous_status(
    link: ResourceCalendarLinkDocument,
    source: BusyTimeSource,
    feed_id: IcalImportFeedId | None,
) -> BusySourceStatus | None:
    if source is BusyTimeSource.GOOGLE:
        return link.google_status
    if source is BusyTimeSource.BOOKING_SYSTEM:
        return None if link.booking_system is None else link.booking_system.status
    return next(
        (feed.status for feed in link.ical_imports if feed.feed_id == feed_id), None
    )
