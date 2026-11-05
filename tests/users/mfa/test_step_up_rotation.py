"""
A step-up that raises a one-factor session to two factors says so
(`is_level_raised`) and answers a one-time rotation ticket: only the token
swapped in with it at POST /v1/auth/session/rotate carries the two factors
and the proof; the old token stays one factor, cannot confirm sensitive
actions, and ends. A step-up that raises nothing records its proof in
place and answers no ticket.
"""

from app.schemas.constants.mfa import AuthLevel
from app.utilities.security.access_tokens import generate_access_token
from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, sign_in_and_create_restaurant
from tests.users.mfa.mfa_api import (
    ROTATE_PATH,
    STEP_UP_SECONDS,
    reason_codes,
    set_up_authenticator,
    store_session,
)

STAFF: dict[str, str] = {"phone_number": "+995 555 77 88 99", "role": "staff"}


def confirm_with_authenticator(
    workshop: Workshop, headers: dict[str, str]
) -> dict[str, object]:
    started = workshop.client.post("/v1/auth/step-up", headers=headers)
    assert started.status_code == 200, started.text
    code = workshop.authenticators.code_for(GEORGIAN_OWNER_PHONE, workshop.clock)
    confirmed = workshop.client.post(
        "/v1/auth/step-up/verify", json={"code": code}, headers=headers
    )
    assert confirmed.status_code == 200, confirmed.text
    return dict(confirmed.json())


def one_factor_session(workshop: Workshop) -> tuple[dict[str, str], str]:
    """The owner with an authenticator, on a one-factor session that is old."""

    token, user_id, business_id = sign_in_and_create_restaurant(workshop)
    set_up_authenticator(workshop, token, GEORGIAN_OWNER_PHONE)
    one_factor = store_session(
        workshop, user_id, str(generate_access_token()), AuthLevel.ONE_FACTOR
    )
    workshop.clock.advance(STEP_UP_SECONDS + 1)
    return one_factor, business_id


def test_a_raised_session_rotates_with_its_ticket(workshop: Workshop) -> None:
    one_factor, business_id = one_factor_session(workshop)

    confirmed = confirm_with_authenticator(workshop, one_factor)
    # Until the swap the old token proves nothing new.
    waiting = workshop.client.post(
        f"/v1/businesses/{business_id}/members", json=STAFF, headers=one_factor
    )
    rotated = workshop.client.post(
        ROTATE_PATH,
        json={"rotation_ticket": confirmed["rotation_ticket"]},
        headers=one_factor,
    )

    assert (confirmed["auth_level"], confirmed["is_level_raised"]) == (
        "two_factor",
        True,
    )
    assert waiting.status_code == 401
    assert reason_codes(waiting) == ["step_up_required"]
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["auth_level"] == "two_factor"
    fresh = bearer(str(rotated.json()["access_token"]))
    old_security = workshop.client.get("/v1/me/security", headers=one_factor).json()
    assert old_security["auth_level"] == "one_factor"
    # The old token, in its last seconds, cannot do a step-up-guarded action.
    refused = workshop.client.post(
        f"/v1/businesses/{business_id}/members", json=STAFF, headers=one_factor
    )
    assert refused.status_code == 401
    assert reason_codes(refused) == ["step_up_required"]
    allowed = workshop.client.post(
        f"/v1/businesses/{business_id}/members", json=STAFF, headers=fresh
    )
    assert allowed.status_code == 201, allowed.text
    workshop.clock.advance(31)
    assert workshop.client.get("/v1/me", headers=one_factor).status_code == 401
    assert workshop.client.get("/v1/me/security", headers=fresh).json()[
        "auth_level"
    ] == ("two_factor")


def test_rotating_without_the_ticket_or_twice_is_refused(workshop: Workshop) -> None:
    one_factor, _ = one_factor_session(workshop)
    confirmed = confirm_with_authenticator(workshop, one_factor)
    ticket = {"rotation_ticket": confirmed["rotation_ticket"]}

    without = workshop.client.post(ROTATE_PATH, headers=one_factor)
    guessed = workshop.client.post(
        ROTATE_PATH,
        json={"rotation_ticket": str(generate_access_token())},
        headers=one_factor,
    )
    first = workshop.client.post(ROTATE_PATH, json=ticket, headers=one_factor)
    again = workshop.client.post(ROTATE_PATH, json=ticket, headers=one_factor)
    with_new_token = workshop.client.post(
        ROTATE_PATH, json=ticket, headers=bearer(str(first.json()["access_token"]))
    )

    assert without.status_code == 422, without.text
    assert guessed.status_code == 409, guessed.text
    assert first.status_code == 200, first.text
    assert (again.status_code, with_new_token.status_code) == (409, 409)


def test_a_two_factor_session_raises_nothing(workshop: Workshop) -> None:
    token, _, _ = sign_in_and_create_restaurant(workshop)
    token, _ = set_up_authenticator(workshop, token, GEORGIAN_OWNER_PHONE)
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    confirmed = confirm_with_authenticator(workshop, bearer(token))

    assert (
        confirmed["auth_level"],
        confirmed["is_level_raised"],
        confirmed["rotation_ticket"],
    ) == ("two_factor", False, None)


def test_a_login_code_raises_nothing(workshop: Workshop) -> None:
    token, _, _ = sign_in_and_create_restaurant(workshop)
    workshop.clock.advance(STEP_UP_SECONDS + 1)
    started = workshop.client.post("/v1/auth/step-up", headers=bearer(token))

    confirmed = workshop.client.post(
        "/v1/auth/step-up/verify",
        json={
            "challenge_id": started.json()["login_code"]["challenge_id"],
            "login_code": str(workshop.otp.codes[-1].code),
        },
        headers=bearer(token),
    )

    assert confirmed.status_code == 200, confirmed.text
    assert (
        confirmed.json()["auth_level"],
        confirmed.json()["is_level_raised"],
        confirmed.json()["rotation_ticket"],
    ) == ("one_factor", False, None)
