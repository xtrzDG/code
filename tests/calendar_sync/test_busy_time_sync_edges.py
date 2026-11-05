"""
The sync facilitator at its edges: a source unlinked while it was read is
forgotten, an unexpected failure of one source is a provider error, HTTP
errors of a feed explain themselves, availability spends one short budget
on stale calendars and never fails because of them, and an older read
never replaces a newer one.
"""

import pytest
from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.calendar_sync_repositories import CalendarBusyTimesRepository
from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.domain.calendar_sync import (
    BusyBlock,
    CalendarBusyTimesDocument,
    ResourceCalendarLinkDocument,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.utilities.calendar_sync.calendar_sync_keys import busy_times_id_of
from tests.calendar_sync.calendar_shop import (
    FEED_URL,
    OPEN_ALL_WEEK,
    OTHER_FEED_URL,
    calendar_ics,
    open_calendar_shop,
)

PARTY: str = "UID:p\r\nDTSTART:20261006T100000Z\r\nDTEND:20261006T110000Z"


def test_a_feed_unlinked_while_it_was_read_is_forgotten() -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.serve(FEED_URL, calendar_ics(PARTY))
        shop.import_feed()
        link_repo = shop.workshop.container.repositories.resource_calendar_link_repo()

        def unlink_meanwhile(url: str) -> None:
            del url

            def drop(
                link: ResourceCalendarLinkDocument,
            ) -> ResourceCalendarLinkDocument:
                link.ical_imports = []
                return link

            link_repo.update(
                BusinessId(shop.business_id), ResourceId(shop.resource_id), drop
            )

        shop.edges.feeds.on_fetch = unlink_meanwhile
        synced = shop.post(f"{shop.calendar}/sync")
        shop.edges.feeds.on_fetch = None
        free = shop.free_times()

    assert synced.status_code == 200, synced.text
    assert synced.json()["ical_imports"] == []
    assert synced.json()["upcoming_busy_times"] == []
    assert "14:00" in free


def test_an_unexpected_failure_of_a_source_is_a_provider_error() -> None:
    def explode(url: str) -> None:
        raise RuntimeError(f"bug while reading {url}")

    with open_calendar_shop() as shop:
        shop.edges.feeds.on_fetch = explode
        imported = shop.import_feed()

    status = imported.json()["ical_imports"][0]["status"]
    assert status["problem"] == "provider_error"
    assert FEED_URL not in str(status["problem_detail"])


@pytest.mark.parametrize(
    ("status", "problem"),
    [(401, "access_denied"), (410, "not_found"), (503, "provider_error")],
)
def test_http_errors_of_a_feed_explain_themselves(status: int, problem: str) -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.statuses[FEED_URL] = status
        imported = shop.import_feed()

    assert imported.json()["ical_imports"][0]["status"]["problem"] == problem


def test_an_unknown_host_is_unreachable() -> None:
    with open_calendar_shop() as shop:
        imported = shop.import_feed()

    assert imported.json()["ical_imports"][0]["status"]["problem"] == "unreachable"


def test_availability_spends_one_short_budget_on_stale_calendars() -> None:
    with open_calendar_shop() as shop:
        second = shop.post(
            f"{shop.base}/resources",
            {"name": "Terrace", "capacity": 4, "schedule": OPEN_ALL_WEEK},
        ).json()["id"]
        shop.edges.feeds.serve(FEED_URL, calendar_ics(PARTY))
        shop.edges.feeds.serve(OTHER_FEED_URL, calendar_ics(PARTY))
        shop.import_feed()
        shop.post(
            f"{shop.base}/resources/{second}/calendar/ical-imports",
            {"url": OTHER_FEED_URL},
        )
        shop.workshop.clock.advance(901)
        reads_before = len(shop.edges.feeds.fetched)
        # The first read takes all 2 s availability may spend on stale ones.
        shop.edges.feeds.on_fetch = lambda _: shop.workshop.clock.advance(2)
        shown = shop.get(f"{shop.base}/availability", date="2026-10-06", party_size="2")
        reads_after = len(shop.edges.feeds.fetched)

    assert shown.status_code == 200, shown.text
    assert reads_after == reads_before + 1


def test_availability_is_shown_when_refreshing_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_: object) -> None:
        raise RuntimeError("storage hiccup")

    with open_calendar_shop() as shop:
        facilitator = shop.workshop.container.facilitators.busy_time_sync()
        monkeypatch.setattr(facilitator, "_refresh_stale", broken)
        free = shop.free_times()

    assert "14:00" in free


def busy_times(fetched_at: int, starts_at: int) -> CalendarBusyTimesDocument:
    resource = ResourceId("resource_00000000-0000-4000-8000-000000000001")
    return CalendarBusyTimesDocument(
        id=busy_times_id_of(resource, BusyTimeSource.GOOGLE, None),
        business_id=BusinessId("business_00000000-0000-4000-8000-000000000001"),
        resource_id=resource,
        source=BusyTimeSource.GOOGLE,
        blocks=[
            BusyBlock(
                starts_at=BusyStartsAtUnixSeconds(starts_at),
                ends_at=BusyEndsAtUnixSeconds(starts_at + 60),
            )
        ],
        covers_until=BusyEndsAtUnixSeconds(10_000),
        fetched_at=Microseconds(fetched_at),
        created_at=Microseconds(fetched_at),
        updated_at=Microseconds(fetched_at),
    )


def test_an_older_read_never_replaces_a_newer_one() -> None:
    repo = CalendarBusyTimesRepository(
        InMemoryDocumentCollectionAdapter[CalendarBusyTimesDocument](
            CalendarBusyTimesDocument
        )
    )

    first = repo.store_if_newer(busy_times(fetched_at=20, starts_at=100))
    older = repo.store_if_newer(busy_times(fetched_at=10, starts_at=200))
    newer = repo.store_if_newer(busy_times(fetched_at=30, starts_at=300))

    stored = repo.list_by_business(busy_times(0, 0).business_id)
    assert (first, older, newer) == (True, False, True)
    assert [int(block.starts_at) for block in stored[0].blocks] == [300]
    assert int(stored[0].created_at) == 20
