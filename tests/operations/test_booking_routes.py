"""Booking routes: the lifecycle, paging and filters, and the cancel language."""

from tests.operations.operations_api import STAFF_TOKEN, Api


def test_booking_lifecycle_through_the_cabinet() -> None:
    api = Api()

    created = api.send(
        "POST",
        "/bookings",
        {
            "contact_name": "Levan",
            "contact_phone_number": "599 12 34 56",
            "date": "2026-10-06",
            "time": "19:00",
            "party_size": 3,
            "source_channel": "phone",
            "notes": "Birthday",
        },
    )
    assert created.status_code == 201, created.text
    booking = created.json()["booking"]
    assert booking["contact_phone_number"] == "+995599123456"
    assert booking["status"] == "confirmed"
    assert "Levan" in created.json()["confirmation_text"]

    listed = api.get("/bookings", **{"from": "2026-10-06", "to": "2026-10-06"})
    assert [item["id"] for item in listed.json()["items"]] == [booking["id"]]
    assert api.get("/bookings", status="cancelled").json()["items"] == []

    moved = api.send(
        "POST",
        f"/bookings/{booking['id']}/reschedule",
        {"new_date": "2026-10-07", "new_time": "20:00"},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["booking"]["date"] == "2026-10-07"

    completed = api.send("PATCH", f"/bookings/{booking['id']}", {"status": "completed"})
    assert completed.json()["status"] == "completed"
    refused = api.send("POST", f"/bookings/{booking['id']}/cancel")
    assert refused.status_code == 409

    assert api.send("POST", "/bookings/booking_nope/cancel").status_code == 404
    noted = api.send("PATCH", f"/bookings/{booking['id']}", {"notes": "Paid"})
    assert noted.json()["notes"] == "Paid"
    invalid = api.send("PATCH", f"/bookings/{booking['id']}", {"status": "maybe"})
    assert invalid.status_code == 422
    assert "status" in invalid.json()["message"]
    extra = api.send(
        "POST", f"/bookings/{booking['id']}/reschedule", {"new_date": "x", "a": 1}
    )
    assert extra.status_code == 422


def test_booking_list_pages_and_filters_by_resource() -> None:
    api = Api()
    hall = api.world.add_resource(api.business, "Hall", capacity=40)
    for time, resource_id in (("13:00", None), ("19:00", None), ("19:00", hall.id)):
        created = api.send(
            "POST",
            "/bookings",
            {
                "contact_name": "Levan",
                "date": "2026-10-06",
                "time": time,
                "party_size": 2,
                "resource_id": None if resource_id is None else str(resource_id),
                "country_hint": "IT",
                "contact_phone_number": "333 123 4567",
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["booking"]["contact_phone_number"] == "+393331234567"

    first = api.get("/bookings", limit="2").json()
    rest = api.get("/bookings", limit="2", cursor=first["next_cursor"]).json()
    in_hall = api.get("/bookings", resource_id=str(hall.id)).json()
    latest = api.get("/bookings", order="latest_first", limit="1").json()

    assert [item["time"] for item in first["items"]] == ["13:00", "19:00"]
    assert len(rest["items"]) == 1
    assert rest["next_cursor"] is None
    assert [item["resource_name"] for item in in_hall["items"]] == ["Hall"]
    assert latest["items"][0]["time"] == "19:00"
    assert api.get("/bookings", limit="0").status_code == 422
    assert api.get("/bookings", cursor="not a cursor").status_code == 422
    assert api.get("/bookings", order="sideways").status_code == 422


def test_cabinet_cancel_uses_the_requested_language() -> None:
    api = Api()
    created = api.send(
        "POST",
        "/bookings",
        {
            "contact_name": "Levan",
            "date": "2026-10-06",
            "time": "19:00",
            "party_size": 2,
        },
    ).json()["booking"]

    response = api.client.post(
        api.url(f"/bookings/{created['id']}/cancel"),
        params={"language": "en"},
        headers={"Authorization": f"Bearer {STAFF_TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json()["confirmation_text"].startswith(
        "Your booking at Salobie Bia on Tuesday, October 6, 2026, 19:00 is cancelled."
    )
