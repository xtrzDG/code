"""
iCal feeds through the real application: an imported feed's busy times take
the table's slots, a refused address or a sixth feed is explained, the
address is never shown back, and removing the feed frees the slots again.
"""

from tests.calendar_sync.calendar_shop import (
    FEED_URL,
    OTHER_FEED_URL,
    calendar_ics,
    open_calendar_shop,
)

# 14:00-16:00 in Tbilisi on the day the shop looks at.
DINNER_PARTY: str = "UID:party-1\r\nDTSTART:20261006T100000Z\r\nDTEND:20261006T120000Z"


def test_an_imported_busy_time_removes_its_slots() -> None:
    with open_calendar_shop() as shop:
        before = shop.free_times()
        shop.edges.feeds.serve(FEED_URL, calendar_ics(DINNER_PARTY))
        imported = shop.import_feed()
        after = shop.free_times()
        view = shop.view()

    assert imported.status_code == 201, imported.text
    assert {"13:30", "14:00", "15:00", "15:30"} <= set(before)
    assert after == ["12:00", "12:30", "13:00", "16:00"]
    feed = view["ical_imports"][0]
    assert feed["host"] == "www.airbnb.com"
    assert feed["status"]["block_count"] == 1
    assert feed["status"]["problem"] is None
    assert "test-feed-0000" not in str(view)
    assert view["upcoming_busy_times"][0]["source"] == "ical"
    assert view["upcoming_busy_times"][0]["feed_host"] == "www.airbnb.com"


def test_removing_the_feed_frees_its_slots() -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.serve(FEED_URL, calendar_ics(DINNER_PARTY))
        feed_id = shop.import_feed().json()["ical_imports"][0]["feed_id"]
        removed = shop.delete(f"{shop.calendar}/ical-imports/{feed_id}")
        after = shop.free_times()
        view = shop.view()

    assert removed.status_code == 204, removed.text
    assert {"14:00", "15:00"} <= set(after)
    assert view["ical_imports"] == []
    assert view["upcoming_busy_times"] == []


def test_a_feed_that_cannot_be_read_is_kept_with_its_reason() -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.slow.add(FEED_URL)
        imported = shop.import_feed()
        free = shop.free_times()

    assert imported.status_code == 201, imported.text
    status = imported.json()["ical_imports"][0]["status"]
    assert status["problem"] == "timeout"
    assert status["last_synced_at"] is None
    assert {"14:00", "15:00"} <= set(free)


def test_a_failed_read_keeps_the_busy_times_read_before() -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.serve(FEED_URL, calendar_ics(DINNER_PARTY))
        shop.import_feed()
        shop.edges.feeds.serve(FEED_URL, "<html>maintenance</html>")
        synced = shop.post(f"{shop.calendar}/sync")
        free = shop.free_times()

    assert synced.status_code == 200, synced.text
    status = synced.json()["ical_imports"][0]["status"]
    assert status["problem"] == "not_a_calendar"
    assert status["last_synced_at"] is not None
    assert status["block_count"] == 1
    assert "14:00" not in free


def test_private_and_unusual_addresses_are_refused() -> None:
    with open_calendar_shop() as shop:
        private = shop.import_feed("https://127.0.0.1/calendar.ics")
        ftp = shop.import_feed("ftp://www.airbnb.com/calendar.ics")
        nothing_read = list(shop.edges.feeds.fetched)
        view = shop.view()

    assert private.status_code == 422, private.text
    assert private.json()["reasons"][0]["code"] == "address_refused"
    assert ftp.status_code == 422, ftp.text
    assert nothing_read == []
    assert view["ical_imports"] == []


def test_the_same_feed_twice_and_a_sixth_feed_are_refused() -> None:
    with open_calendar_shop() as shop:
        addresses = [f"{OTHER_FEED_URL}&n={number}" for number in range(5)]
        for address in addresses:
            shop.edges.feeds.serve(address, calendar_ics())
            assert shop.import_feed(address).status_code == 201
        again = shop.import_feed(addresses[0])
        shop.edges.feeds.serve(FEED_URL, calendar_ics())
        sixth = shop.import_feed(FEED_URL)

    assert again.status_code == 422, again.text
    assert again.json()["reasons"][0]["code"] == "feed_already_imported"
    assert sixth.status_code == 422, sixth.text
    assert sixth.json()["reasons"][0]["code"] == "feed_limit"


def test_webcal_addresses_are_read_over_https() -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.serve(FEED_URL, calendar_ics(DINNER_PARTY))
        imported = shop.import_feed(FEED_URL.replace("https://", "webcal://"))
        fetched = list(shop.edges.feeds.fetched)

    assert imported.status_code == 201, imported.text
    assert fetched == [FEED_URL]
    assert imported.json()["ical_imports"][0]["status"]["block_count"] == 1
