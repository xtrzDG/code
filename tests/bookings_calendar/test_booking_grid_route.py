"""GET …/bookings/grid as the cabinet calls it: the window, its flags and refusals."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.booking_calendar_routes import build_booking_calendar_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.bookings_calendar.grid_world import GridWorld
from tests.foundation.access_support import ACCESS_SETTINGS
from tests.foundation.support_access_builders import build_authorize_business_access
from tests.operations.operations_api import TokenAuthenticator, operator

STAFF_TOKEN = "staff-token"
STRANGER_TOKEN = "stranger-token"


def client_of(world: GridWorld) -> TestClient:
    application = FastAPI()
    install_error_handlers(application)
    store = world.world
    application.include_router(
        build_booking_calendar_router(
            current_user=build_current_user_dependency(
                TokenAuthenticator(
                    {STAFF_TOKEN: world.staff_id, STRANGER_TOKEN: UserId()}
                ),
                SessionAssuranceContext(),
            ),
            authorize_business_access=operator(
                build_authorize_business_access(
                    business_repo=store.business_repo,
                    user_repo=store.user_repo,
                    audit_log_repo=store.audit_repo,
                    wall_clock=store.clock.wall_clock,
                    session_assurance=SessionAssuranceContext(),
                    app_settings=ACCESS_SETTINGS,
                )
            ),
            booking_grid=operator(world.use_case()),
        )
    )
    return TestClient(application)


def test_the_grid_of_a_week_with_and_without_names() -> None:
    world = GridWorld()
    world.book(world.window, "2026-10-07T19:00", "2026-10-07T21:00")
    world.book(world.hall, "2026-10-07T19:00", "2026-10-07T21:00", is_sandbox=True)
    client = client_of(world)
    path = f"/v1/businesses/{world.business.id}/bookings/grid"
    headers = {"Authorization": f"Bearer {STAFF_TOKEN}"}

    week = client.get(path, params={"date": "2026-10-05", "days": "7"}, headers=headers)
    assert week.status_code == 200, week.text
    body = week.json()
    assert (body["date_from"], body["date_to"]) == ("2026-10-05", "2026-10-11")
    assert len(body["days"]) == 7
    assert [item["time"] for item in body["bookings"]] == ["19:00"]
    assert body["days"][2]["places"][0]["booked_unit_minutes"] == 120

    counts = client.get(
        path,
        params={
            "date": "2026-10-07",
            "include_bookings": "false",
            "include_sandbox": "1",
        },
        headers=headers,
    ).json()
    assert counts["bookings"] == []
    assert len(counts["days"]) == 1
    assert [place["booking_count"] for place in counts["days"][0]["places"]] == [
        1,
        0,
        1,
    ]


def test_bad_windows_and_strangers_are_refused() -> None:
    world = GridWorld()
    client = client_of(world)
    path = f"/v1/businesses/{world.business.id}/bookings/grid"
    headers = {"Authorization": f"Bearer {STAFF_TOKEN}"}

    assert (
        client.get(path, params={"date": "06.10.2026"}, headers=headers).status_code
        == 422
    )
    too_long = client.get(
        path, params={"date": "2026-10-06", "days": "32"}, headers=headers
    )
    assert too_long.status_code == 422
    assert "days" in too_long.json()["message"]
    assert client.get(path, params={"days": "7"}, headers=headers).status_code == 422
    stranger = client.get(
        path,
        params={"date": "2026-10-06"},
        headers={"Authorization": f"Bearer {STRANGER_TOKEN}"},
    )
    assert stranger.status_code == 404
