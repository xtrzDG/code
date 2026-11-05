"""
Busy times stay current: the five-minute job reads the calendars that are
due (and only those), availability reads stale ones itself within its short
budget, and settings of a resource that is gone are never read again.
"""

from typed_time_provider import Microseconds

from app.gateways.worker.periodic.calendar_sync import SYNC_CALENDARS_JOB
from app.schemas.domain.calendar_sync import ResourceCalendarLinkDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.calendar_sync.calendar_sync_keys import (
    resource_calendar_link_id_of,
)
from tests.calendar_sync.calendar_shop import (
    FEED_URL,
    CalendarShop,
    calendar_ics,
    open_calendar_shop,
)

# 14:00-15:00, then 16:00-17:00 in Tbilisi.
EARLY: str = "UID:a\r\nDTSTART:20261006T100000Z\r\nDTEND:20261006T110000Z"
LATE: str = "UID:b\r\nDTSTART:20261006T120000Z\r\nDTEND:20261006T130000Z"


def run_job(shop: CalendarShop) -> JobReport:
    container = shop.workshop.container
    now = container.time_provider.microsecond_wall_clock().now_unix()
    operator = container.operators.calendars.sync_due_calendars_operator()
    return operator.operate(JobTick(job_name=SYNC_CALENDARS_JOB, scheduled_at=now))


def test_the_job_reads_calendars_once_they_are_due() -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.serve(FEED_URL, calendar_ics(EARLY))
        shop.import_feed()
        shop.edges.feeds.serve(FEED_URL, calendar_ics(LATE))
        too_early = run_job(shop)
        reads_before = len(shop.edges.feeds.fetched)
        shop.workshop.clock.advance(300)
        due = run_job(shop)
        reads_after = len(shop.edges.feeds.fetched)
        free = shop.free_times()

    assert too_early.processed_count == 0
    assert due.processed_count == 1
    assert reads_after == reads_before + 1
    assert free == ["12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00"]


def test_availability_reads_stale_calendars_itself() -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.serve(FEED_URL, calendar_ics(EARLY))
        shop.import_feed()
        shop.edges.feeds.serve(FEED_URL, calendar_ics(LATE))
        fresh = shop.free_times()
        shop.workshop.clock.advance(901)
        stale = shop.free_times()
        limits = list(shop.edges.feeds.time_limits)

    assert "14:00" not in fresh and "16:00" in fresh
    assert "14:00" in stale and "16:00" not in stale
    # The import read within 2 s; availability's read within what is left of 2 s.
    assert limits[0] == 2.0
    assert 0 < limits[-1] <= 2.0


def test_settings_of_a_resource_that_is_gone_are_not_read_again() -> None:
    with open_calendar_shop() as shop:
        container = shop.workshop.container
        business_id = BusinessId(shop.business_id)
        gone = ResourceId("resource_00000000-0000-4000-8000-000000000000")
        link_repo = container.repositories.resource_calendar_link_repo()
        with container.utilities.storage_scope().scoped_to_business(business_id):
            link_repo.add(
                ResourceCalendarLinkDocument(
                    id=resource_calendar_link_id_of(gone),
                    business_id=business_id,
                    resource_id=gone,
                    next_sync_at=Microseconds(1),
                    created_at=Microseconds(1),
                    updated_at=Microseconds(1),
                )
            )
        report = run_job(shop)
        with container.utilities.storage_scope().scoped_to_business(business_id):
            stored = link_repo.get(business_id, gone)

    assert report.processed_count == 0
    assert stored is not None
    assert stored.next_sync_at is None
