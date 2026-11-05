"""
Staff bookings respect busy times from outside the platform, Settings →
Integrations says what each integration does for the business, and only
owners change a resource's calendars.
"""

from tests.calendar_sync.calendar_shop import FEED_URL, calendar_ics, open_calendar_shop
from tests.calendar_sync.fake_cal_com import GOOD_KEY
from tests.e2e.harness import bearer

DINNER_PARTY: str = "UID:party-1\r\nDTSTART:20261006T100000Z\r\nDTEND:20261006T120000Z"
STAFF_PHONE: str = "+995 555 44 33 22"


def test_a_staff_booking_at_a_busy_time_is_refused() -> None:
    with open_calendar_shop() as shop:
        shop.edges.feeds.serve(FEED_URL, calendar_ics(DINNER_PARTY))
        shop.import_feed()
        busy = shop.book("14:30")
        free = shop.book("16:00")

    assert busy.status_code == 409, busy.text
    assert free.status_code == 201, free.text


def test_integrations_list_what_each_integration_does() -> None:
    with open_calendar_shop() as shop:
        before = shop.get(f"{shop.base}/integrations").json()
        shop.edges.feeds.serve(FEED_URL, calendar_ics(DINNER_PARTY))
        shop.import_feed()
        shop.post(f"{shop.calendar}/ical-export")
        shop.put(
            f"{shop.calendar}/booking-system",
            {"kind": "cal_com", "external_resource_id": "1203845", "api_key": GOOD_KEY},
        )
        shop.edges.feeds.slow.add(FEED_URL)
        shop.post(f"{shop.calendar}/sync")
        after = shop.get(f"{shop.base}/integrations").json()

    states_before = {item["kind"]: item["state"] for item in before["items"]}
    assert states_before == {
        "google_calendar": "off",
        "ical_import": "off",
        "ical_export": "off",
        "cal_com": "off",
    }
    by_kind = {item["kind"]: item for item in after["items"]}
    assert by_kind["ical_import"]["state"] == "attention"
    assert by_kind["ical_export"]["state"] == "on"
    assert by_kind["cal_com"]["state"] == "on"
    assert by_kind["cal_com"]["resource_count"] == 1
    assert before["resources"] == []
    [summary] = after["resources"]
    assert summary["resource_id"] == shop.resource_id
    assert (summary["source_count"], summary["problem_count"]) == (2, 1)
    assert summary["is_export_on"] is True
    assert summary["last_synced_at"] is not None


def test_a_connected_google_account_is_on_for_integrations() -> None:
    with open_calendar_shop() as shop:
        shop.connect_google()
        listed = shop.get(f"{shop.base}/integrations").json()

    by_kind = {item["kind"]: item for item in listed["items"]}
    assert by_kind["google_calendar"]["state"] == "on"


def test_staff_see_a_resource_calendar_but_cannot_change_it() -> None:
    with open_calendar_shop() as shop:
        invited = shop.post(
            f"{shop.base}/members",
            {"phone_number": STAFF_PHONE, "role": "staff"},
        )
        staff_token, _ = shop.workshop.sign_in_with_phone(STAFF_PHONE)
        staff = bearer(staff_token)
        seen = shop.client.get(shop.calendar, headers=staff)
        changed = shop.client.post(
            f"{shop.calendar}/ical-imports", json={"url": FEED_URL}, headers=staff
        )
        integrations = shop.client.get(f"{shop.base}/integrations", headers=staff)

    assert invited.status_code in {200, 201}, invited.text
    assert seen.status_code == 200, seen.text
    assert changed.status_code == 403, changed.text
    assert integrations.status_code == 403, integrations.text
