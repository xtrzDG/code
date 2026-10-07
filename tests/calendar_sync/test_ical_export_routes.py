"""
The export feed of a table, through the real application: its bookings and
the busy times of its Google calendar as opaque events (no guest's details,
no imported iCal events echoed back), the token kept only as a hash, made
again or removed it stops working, and readers are rate limited.
"""

from urllib.parse import urlsplit

import icalendar

from app.schemas.typings.calendar_sync.strings import IcalExportToken
from app.utilities.calendar_sync.calendar_sync_keys import hash_export_token
from tests.calendar_sync.calendar_shop import FEED_URL, calendar_ics, open_calendar_shop
from tests.calendar_sync.fake_google_calendars import TEAM_CALENDAR

IMPORTED_STAY: str = (
    "UID:stay-1\r\nDTSTART;VALUE=DATE:20261008\r\nDTEND;VALUE=DATE:20261010"
)


def feed_path(url: str) -> str:
    return urlsplit(url).path


def events_of(text: str) -> list[icalendar.Event]:
    calendar = icalendar.Calendar.from_ical(text.encode("utf-8"))
    return [
        component
        for component in calendar.subcomponents
        if isinstance(component, icalendar.Event)
    ]


def test_the_feed_lists_bookings_and_google_busy_times_without_guests() -> None:
    with open_calendar_shop() as shop:
        shop.connect_google()
        shop.google.busy[TEAM_CALENDAR] = [
            ("2026-10-07T10:00:00Z", "2026-10-07T11:00:00Z")
        ]
        shop.put(f"{shop.calendar}/google", {"calendar_id": TEAM_CALENDAR})
        shop.edges.feeds.serve(FEED_URL, calendar_ics(IMPORTED_STAY))
        shop.import_feed()
        assert shop.book("13:00").status_code == 201
        created = shop.post(f"{shop.calendar}/ical-export")
        url = str(created.json()["url"])
        feed = shop.client.get(feed_path(url))
        view = shop.view()

    assert created.status_code == 201, created.text
    assert url.startswith("http") and url.endswith(".ics")
    assert feed.status_code == 200, feed.text
    assert feed.headers["content-type"].startswith("text/calendar")
    assert feed.headers["cache-control"] == "no-store"
    assert feed.headers["x-robots-tag"] == "noindex"
    events = events_of(feed.text)
    starts = sorted(str(event.decoded("dtstart")) for event in events)
    assert starts == ["2026-10-06 09:00:00+00:00", "2026-10-07 10:00:00+00:00"]
    # The business's language (a Georgian restaurant), never a guest's name.
    assert {str(event.get("summary")) for event in events} == {"დაჯავშნილია"}
    assert "Nino" not in feed.text and "555" not in feed.text
    assert "2026-10-08" not in starts[0] and "20261008" not in feed.text
    assert view["ical_export"]["is_on"] is True
    assert view["ical_export"]["last_read_at"] is not None


def test_only_the_hash_of_the_token_is_stored() -> None:
    with open_calendar_shop() as shop:
        url = str(shop.post(f"{shop.calendar}/ical-export").json()["url"])
        token = feed_path(url).rsplit("/", 1)[1].removesuffix(".ics")
        repo = shop.workshop.container.repositories.ical_export_feed_repo()
        storage_scope = shop.workshop.container.utilities.storage_scope()
        with storage_scope.platform_wide():
            stored = repo.find(hash_export_token(IcalExportToken(token)))

    assert stored is not None
    assert token not in stored.model_dump_json()


def test_a_new_address_retires_the_old_one() -> None:
    with open_calendar_shop() as shop:
        first = str(shop.post(f"{shop.calendar}/ical-export").json()["url"])
        second = str(shop.post(f"{shop.calendar}/ical-export").json()["url"])
        old = shop.client.get(feed_path(first))
        new = shop.client.get(feed_path(second))

    assert first != second
    assert old.status_code == 404, old.text
    assert new.status_code == 200, new.text


def test_a_removed_address_and_a_made_up_one_are_not_found() -> None:
    with open_calendar_shop() as shop:
        url = str(shop.post(f"{shop.calendar}/ical-export").json()["url"])
        removed = shop.delete(f"{shop.calendar}/ical-export")
        gone = shop.client.get(feed_path(url))
        made_up = shop.client.get("/v1/public/ical/not-a-real-token-0000.ics")
        view = shop.view()

    assert removed.status_code == 204, removed.text
    assert gone.status_code == 404, gone.text
    assert made_up.status_code == 404, made_up.text
    assert view["ical_export"]["is_on"] is False


def test_readers_of_one_network_are_rate_limited() -> None:
    with open_calendar_shop() as shop:
        url = feed_path(str(shop.post(f"{shop.calendar}/ical-export").json()["url"]))
        statuses = [shop.client.get(url).status_code for _ in range(61)]

    assert statuses[:60] == [200] * 60
    assert statuses[60] == 429
