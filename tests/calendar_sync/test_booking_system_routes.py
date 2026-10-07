"""
Cal.com behind the booking-system connector, through the real application:
a linked event type's bookings take the table's slots, a refused key or an
unknown event type is explained before anything is stored, the key is never
shown back, and a slow Cal.com keeps what was read before.
"""

from tests.calendar_sync.calendar_shop import open_calendar_shop
from tests.calendar_sync.fake_cal_com import GOOD_KEY

LINK: dict[str, str] = {
    "kind": "cal_com",
    "external_resource_id": "1203845",
    "api_key": GOOD_KEY,
}


def test_cal_com_bookings_take_the_slots() -> None:
    with open_calendar_shop() as shop:
        shop.edges.cal_com.book("2026-10-06T10:00:00.000Z", "2026-10-06T11:00:00.000Z")
        shop.edges.cal_com.book(
            "2026-10-06T08:00:00.000Z", "2026-10-06T09:00:00.000Z", "cancelled"
        )
        linked = shop.put(f"{shop.calendar}/booking-system", LINK)
        free = shop.free_times()

    assert linked.status_code == 200, linked.text
    system = linked.json()["booking_system"]
    assert system["kind"] == "cal_com"
    assert system["external_resource_title"] == "Haircut"
    assert system["status"]["block_count"] == 1
    assert GOOD_KEY not in linked.text
    assert free == ["12:00", "12:30", "13:00", "15:00", "15:30", "16:00"]


def test_a_refused_key_is_explained_and_nothing_is_linked() -> None:
    with open_calendar_shop() as shop:
        refused = shop.put(
            f"{shop.calendar}/booking-system", {**LINK, "api_key": "cal_wrong_0000"}
        )
        unknown = shop.put(
            f"{shop.calendar}/booking-system", {**LINK, "external_resource_id": "77"}
        )
        view = shop.view()

    assert refused.status_code == 422, refused.text
    assert refused.json()["reasons"][0]["code"] == "access_denied"
    assert unknown.status_code == 422, unknown.text
    assert unknown.json()["reasons"][0]["code"] == "not_found"
    assert view["booking_system"] is None
    assert view["booking_system_kinds"] == ["cal_com"]


def test_a_slow_cal_com_keeps_the_busy_times_read_before() -> None:
    with open_calendar_shop() as shop:
        shop.edges.cal_com.book("2026-10-06T10:00:00.000Z", "2026-10-06T11:00:00.000Z")
        shop.put(f"{shop.calendar}/booking-system", LINK)
        shop.edges.cal_com.is_slow = True
        synced = shop.post(f"{shop.calendar}/sync")
        free = shop.free_times()

    status = synced.json()["booking_system"]["status"]
    assert status["problem"] == "timeout"
    assert status["block_count"] == 1
    assert "14:00" not in free


def test_a_slow_cal_com_cannot_be_linked() -> None:
    with open_calendar_shop() as shop:
        shop.edges.cal_com.is_slow = True
        linked = shop.put(f"{shop.calendar}/booking-system", LINK)

    assert linked.status_code == 422, linked.text
    assert linked.json()["reasons"][0]["code"] == "timeout"


def test_unlinking_the_booking_system_frees_its_slots() -> None:
    with open_calendar_shop() as shop:
        shop.edges.cal_com.book("2026-10-06T10:00:00.000Z", "2026-10-06T11:00:00.000Z")
        shop.put(f"{shop.calendar}/booking-system", LINK)
        removed = shop.delete(f"{shop.calendar}/booking-system")
        free = shop.free_times()
        view = shop.view()

    assert removed.status_code == 204, removed.text
    assert "14:00" in free
    assert view["booking_system"] is None
