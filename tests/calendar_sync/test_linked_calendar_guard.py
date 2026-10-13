"""
Availability reads busy times only for a business that links a calendar:
`refresh_stale` says whether any resource does (True when it cannot tell),
and without a link nothing could have stored a busy time.
"""

import pytest

from app.repositories.calendar_sync_repositories import CalendarBusyTimesRepository
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.booleans import HasLinkedCalendars
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from tests.calendar_sync.calendar_shop import (
    FEED_URL,
    CalendarShop,
    calendar_ics,
    open_calendar_shop,
)

PARTY: str = "UID:p\r\nDTSTART:20261006T100000Z\r\nDTEND:20261006T110000Z"
BUDGET: BusyTimeFetchSeconds = BusyTimeFetchSeconds(2.0)


def refresh(shop: CalendarShop) -> HasLinkedCalendars:
    business_id = BusinessId(shop.business_id)
    scope = shop.workshop.container.utilities.storage_scope()
    facilitator = shop.workshop.container.facilitators.busy_time_sync()
    with scope.scoped_to_business(business_id):
        return facilitator.refresh_stale(business_id, BUDGET)


@pytest.fixture
def busy_time_reads(monkeypatch: pytest.MonkeyPatch) -> list[BusinessId]:
    reads: list[BusinessId] = []
    read = CalendarBusyTimesRepository.list_by_business

    def counted(
        repository: CalendarBusyTimesRepository, business_id: BusinessId
    ) -> object:
        reads.append(business_id)
        return read(repository, business_id)

    monkeypatch.setattr(CalendarBusyTimesRepository, "list_by_business", counted)
    return reads


def test_a_business_without_linked_calendars_reads_no_busy_times(
    busy_time_reads: list[BusinessId],
) -> None:
    with open_calendar_shop() as shop:
        has_links = refresh(shop)
        free = shop.free_times()

    assert has_links is False
    assert free
    assert busy_time_reads == []


def test_a_linked_calendar_still_blocks_its_times(
    busy_time_reads: list[BusinessId],
) -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.serve(FEED_URL, calendar_ics(PARTY))
        imported = shop.import_feed()
        has_links = refresh(shop)
        free = shop.free_times()

    assert imported.status_code == 201, imported.text
    assert has_links is True
    assert busy_time_reads
    assert "14:00" not in free


def test_a_failed_refresh_reads_the_busy_times_all_the_same(
    monkeypatch: pytest.MonkeyPatch,
    busy_time_reads: list[BusinessId],
) -> None:
    """A refresh that raises cannot tell: the stored busy times still block."""

    def broken(*_: object) -> bool:
        raise RuntimeError("storage hiccup")

    with open_calendar_shop() as shop:
        shop.edges.feeds.serve(FEED_URL, calendar_ics(PARTY))
        imported = shop.import_feed()
        facilitator = shop.workshop.container.facilitators.busy_time_sync()
        monkeypatch.setattr(facilitator, "_refresh_stale", broken)
        busy_time_reads.clear()  # the import's own reads are not availability's
        free = shop.free_times()

    assert imported.status_code == 201, imported.text
    assert busy_time_reads == [BusinessId(shop.business_id)]
    assert free
    assert "14:00" not in free
