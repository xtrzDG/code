"""
Staff revoke the manage links of a booking (AUTHZ-05): every link sent so
far, and every page credential traded for one, stops opening at once (a
new link generation signed inside each link); links of the new generation
open, and the revocation is audited.
"""

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.booking_manage import BookingManageClaims
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.schemas.typings.bookings.prefixed_id import BookingId
from tests.bookings.manage_journey import (
    BOOKINGS_PATH,
    BookedTable,
    book_a_table,
    refusal_codes,
)
from tests.e2e.harness import Workshop, bearer


def claims_of(workshop: Workshop, token: str) -> BookingManageClaims:
    signer = workshop.container.utilities.booking_manage_token_signer()
    claims = signer.read(BookingManageToken(token))
    assert claims is not None
    return claims


def stored_booking(workshop: Workshop, booked: BookedTable) -> BookingDocument:
    claims = claims_of(workshop, booked.token)
    container = workshop.container
    with container.utilities.storage_scope().scoped_to_business(claims.business_id):
        booking = container.repositories.booking_repo().get(
            claims.business_id, claims.booking_id
        )
    assert booking is not None
    return booking


def revoke(workshop: Workshop, booked: BookedTable, booking_id: str) -> int:
    restaurant = booked.restaurant
    return workshop.client.post(
        f"{restaurant.base}/bookings/{booking_id}/manage-links/revoke",
        headers=bearer(restaurant.owner_token),
    ).status_code


def test_revoked_links_and_their_page_credentials_stop_opening(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)
    booking_id = str(claims_of(workshop, booked.token).booking_id)
    session = workshop.client.post(f"{booked.page}/session").json()
    credential_page = f"{BOOKINGS_PATH}/{session['token']}"
    assert workshop.client.get(booked.page).status_code == 200
    assert workshop.client.get(credential_page).status_code == 200

    assert revoke(workshop, booked, booking_id) == 204

    for path in (booked.page, f"{booked.page}/calendar.ics", credential_page):
        refused = workshop.client.get(path)
        assert refused.status_code == 404, (path, refused.text)
        assert refusal_codes(refused) == ["link_expired"]
    exchanged = workshop.client.post(f"{booked.page}/session")
    cancelled = workshop.client.post(f"{booked.page}/cancel")
    assert exchanged.status_code == cancelled.status_code == 404
    assert stored_booking(workshop, booked).status == "confirmed"


def test_a_link_of_the_new_generation_opens(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    claims = claims_of(workshop, booked.token)
    assert int(claims.link_generation) == 0

    assert revoke(workshop, booked, str(claims.booking_id)) == 204
    generation = stored_booking(workshop, booked).manage_link_generation
    signer = workshop.container.utilities.booking_manage_token_signer()
    renewed = signer.sign(claims.model_copy(update={"link_generation": generation}))
    opened = workshop.client.get(f"{BOOKINGS_PATH}/{renewed}")

    assert int(generation) != 0
    assert opened.status_code == 200, opened.text
    # The page's own answers carry the new generation on.
    answered = claims_of(workshop, str(opened.json()["token"]))
    assert answered.link_generation == generation


def test_the_revocation_is_audited_and_unknown_bookings_are_not_found(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)
    restaurant = booked.restaurant
    booking_id = str(claims_of(workshop, booked.token).booking_id)

    assert revoke(workshop, booked, str(BookingId())) == 404
    assert revoke(workshop, booked, booking_id) == 204
    audit = workshop.client.get(
        f"{restaurant.base}/audit-log", headers=bearer(restaurant.owner_token)
    ).json()

    revocations = [
        entry for entry in audit["items"] if entry["entity"] == "booking_manage_links"
    ]
    assert [(entry["action"], entry["entity_id"]) for entry in revocations] == [
        (AuditAction.UPDATE.value, booking_id)
    ]
