"""
The booking page's short-lived credential: the page trades its link's
token for it (POST /v1/public/bookings/{token}/session), so the token can
leave the address bar. The credential opens the same booking on every
route of the page for about 30 minutes, every answer to it carries a
credential that ends no later, it cannot open another credential, and the
link itself keeps working.
"""

from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.bookings.conftest import CABINET_BASE_URL
from tests.bookings.manage_journey import (
    BOOKINGS_PATH,
    BookedTable,
    book_a_table,
    refusal_codes,
)
from tests.e2e.harness import Workshop
from tests.e2e.journeys import JsonObject

SESSION_SECONDS: int = 30 * 60


def open_session(workshop: Workshop, booked: BookedTable) -> JsonObject:
    response = workshop.client.post(f"{booked.page}/session")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    session: JsonObject = response.json()
    return session


def test_the_link_opens_a_credential_of_thirty_minutes(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    now_seconds = int(workshop.clock.wall_clock.now_unix()) // 1_000_000

    session = open_session(workshop, booked)

    assert session["token"] != booked.token
    assert int(session["expires_at"]) == (now_seconds + SESSION_SECONDS) * 1_000_000
    signer = workshop.container.utilities.booking_manage_token_signer()
    claims = signer.read(BookingManageToken(session["token"]))
    link = signer.read(BookingManageToken(booked.token))
    assert claims is not None and link is not None
    assert claims.is_page_session and not link.is_page_session
    assert (claims.business_id, claims.booking_id, claims.booking_version) == (
        link.business_id,
        link.booking_id,
        link.booking_version,
    )


def test_every_route_of_the_page_takes_the_credential(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    session = open_session(workshop, booked)
    page = f"{BOOKINGS_PATH}/{session['token']}"

    view = workshop.client.get(page)
    calendar = workshop.client.get(f"{page}/calendar.ics")
    slots = workshop.client.get(f"{page}/slots", params={"date": "2026-10-07"})

    assert view.status_code == 200, view.text
    assert view.json()["business_name"] == "Salobie Bia"
    assert calendar.status_code == 200, calendar.text
    # The calendar file keeps the guest's own link (it is for later).
    assert f"{CABINET_BASE_URL}/r/" in calendar.text
    assert slots.status_code == 200, slots.text
    # The answer carries a credential again, never the long-lived link.
    signer = workshop.container.utilities.booking_manage_token_signer()
    answered = signer.read(BookingManageToken(view.json()["token"]))
    assert answered is not None and answered.is_page_session
    assert int(answered.expires_at) == int(session["expires_at"])


def test_a_cancellation_through_the_credential_answers_with_a_credential(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)
    session = open_session(workshop, booked)

    cancelled = workshop.client.post(f"{BOOKINGS_PATH}/{session['token']}/cancel")

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    signer = workshop.container.utilities.booking_manage_token_signer()
    answered = signer.read(BookingManageToken(cancelled.json()["token"]))
    assert answered is not None and answered.is_page_session
    assert int(answered.expires_at) <= int(session["expires_at"])


def test_the_credential_expires_and_the_link_keeps_working(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    session = open_session(workshop, booked)

    workshop.clock.advance(SESSION_SECONDS + 1)

    expired = workshop.client.get(f"{BOOKINGS_PATH}/{session['token']}")
    assert expired.status_code == 404
    assert refusal_codes(expired) == ["link_expired"]
    # Old links keep working: the page simply opens a new credential.
    assert workshop.client.get(booked.page).status_code == 200
    assert workshop.client.post(f"{booked.page}/session").status_code == 200


def test_a_credential_cannot_open_another_one(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    session = open_session(workshop, booked)

    again = workshop.client.post(f"{BOOKINGS_PATH}/{session['token']}/session")

    assert again.status_code == 404
    assert refusal_codes(again) == ["link_invalid"]


def test_a_forged_token_opens_no_credential(workshop: Workshop) -> None:
    book_a_table(workshop)

    forged = workshop.client.post(f"{BOOKINGS_PATH}/{'A' * 76}/session")

    assert forged.status_code == 404
    assert refusal_codes(forged) == ["link_invalid"]


def test_credentials_are_limited_per_link(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    answers = [
        workshop.client.post(f"{booked.page}/session").status_code for _ in range(11)
    ]

    assert answers[:10] == [200] * 10
    assert answers[10] == 429


def test_the_page_names_the_business_privacy_notice(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    view: JsonObject = workshop.client.get(booked.page).json()

    # No notice of its own: the platform's default notice of its chat page.
    assert view["privacy_url"] == (
        f"{CABINET_BASE_URL}/c/{booked.restaurant.business_id}/privacy"
    )


def test_the_business_own_privacy_notice_comes_first(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    container = workshop.container
    business_id = BusinessId(booked.restaurant.business_id)
    profiles = container.repositories.business_profile_repo()
    with container.utilities.storage_scope().scoped_to_business(business_id):
        profile = profiles.get_by_business(business_id)
        assert profile is not None
        profile.privacy_notice_url = WebLink("https://salobie.example/privacy")
        profiles.save(profile)

    view: JsonObject = workshop.client.get(booked.page).json()

    assert view["privacy_url"] == "https://salobie.example/privacy"
