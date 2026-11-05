"""POST …/reschedule as the calendar sends it: the place dropped on, the start shown."""

from tests.operations.operations_api import Api


def test_the_calendar_drops_a_booking_on_another_table_and_undoes_it() -> None:
    api = Api()
    terrace = api.world.add_resource(api.business, "Terrace", capacity=6)
    created = api.send(
        "POST",
        "/bookings",
        {
            "contact_name": "Levan",
            "date": "2026-10-06",
            "time": "19:00",
            "party_size": 2,
            "source_channel": "phone",
        },
    ).json()["booking"]
    path = f"/bookings/{created['id']}/reschedule"

    moved = api.send(
        "POST",
        path,
        {
            "new_date": "2026-10-06",
            "new_time": "20:30",
            "new_resource_id": str(terrace.id),
            "expected_date": "2026-10-06",
            "expected_time": "19:00",
        },
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["booking"]["resource_name"] == "Terrace"
    assert moved.json()["booking"]["time"] == "20:30"

    stale = api.send(
        "POST",
        path,
        {
            "new_date": "2026-10-06",
            "new_time": "19:00",
            "new_resource_id": created["resource_id"],
            "expected_date": "2026-10-06",
            "expected_time": "19:00",
        },
    )
    assert stale.status_code == 409
    assert [reason["code"] for reason in stale.json()["reasons"]] == ["booking_changed"]

    undone = api.send(
        "POST",
        path,
        {
            "new_date": "2026-10-06",
            "new_time": "19:00",
            "new_resource_id": created["resource_id"],
            "expected_date": "2026-10-06",
            "expected_time": "20:30",
        },
    )
    assert undone.status_code == 200, undone.text
    assert undone.json()["booking"]["resource_id"] == created["resource_id"]

    unknown = api.send(
        "POST",
        path,
        {"new_date": "2026-10-06", "new_time": "21:00", "new_resource_id": "nope"},
    )
    assert unknown.status_code == 422
