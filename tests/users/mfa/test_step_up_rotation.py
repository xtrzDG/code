"""
A step-up that raises a one-factor session to two factors says so
(`is_level_raised`), and that session then gets a fresh token at POST
/v1/auth/session/rotate; a step-up that raises nothing says it does not.
"""

from app.schemas.constants.mfa import AuthLevel
from app.utilities.security.access_tokens import generate_access_token
from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, sign_in_and_create_restaurant
from tests.users.mfa.mfa_api import STEP_UP_SECONDS, set_up_authenticator, store_session

ROTATE_PATH: str = "/v1/auth/session/rotate"


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


def test_a_raised_session_says_so_and_rotates(workshop: Workshop) -> None:
    token, user_id, _ = sign_in_and_create_restaurant(workshop)
    set_up_authenticator(workshop, token, GEORGIAN_OWNER_PHONE)
    one_factor_token = str(generate_access_token())
    one_factor = store_session(
        workshop, user_id, one_factor_token, AuthLevel.ONE_FACTOR
    )
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    confirmed = confirm_with_authenticator(workshop, one_factor)
    rotated = workshop.client.post(ROTATE_PATH, headers=one_factor)

    assert (confirmed["auth_level"], confirmed["is_level_raised"]) == (
        "two_factor",
        True,
    )
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["auth_level"] == "two_factor"
    assert rotated.json()["access_token"] != one_factor_token
    workshop.clock.advance(31)
    assert workshop.client.get("/v1/me", headers=one_factor).status_code == 401
    fresh = bearer(str(rotated.json()["access_token"]))
    assert workshop.client.get("/v1/me/security", headers=fresh).json()[
        "auth_level"
    ] == ("two_factor")


def test_a_two_factor_session_raises_nothing(workshop: Workshop) -> None:
    token, _, _ = sign_in_and_create_restaurant(workshop)
    set_up_authenticator(workshop, token, GEORGIAN_OWNER_PHONE)
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    confirmed = confirm_with_authenticator(workshop, bearer(token))

    assert (confirmed["auth_level"], confirmed["is_level_raised"]) == (
        "two_factor",
        False,
    )


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
    assert (confirmed.json()["auth_level"], confirmed.json()["is_level_raised"]) == (
        "one_factor",
        False,
    )
