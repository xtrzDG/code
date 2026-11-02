"""
A passkey that confirms a one-factor session does not raise it in place:
the answer says the level is raised (`is_level_raised`) and carries a
one-time rotation ticket, and only the token the cabinet swaps in with it
counts as two factors. A session that already had two factors records the
proof and answers no ticket.
"""

from app.schemas.constants.mfa import AuthLevel
from app.utilities.security.access_tokens import generate_access_token
from tests.e2e.harness import Workshop, bearer
from tests.users.mfa.mfa_api import ROTATE_PATH, STEP_UP_SECONDS, store_session
from tests.users.passkeys.passkey_api import new_authenticator, sign_up_with_passkey
from tests.users.passkeys.software_authenticator import SoftwareAuthenticator


def confirm_with_passkey(
    workshop: Workshop, authenticator: SoftwareAuthenticator, headers: dict[str, str]
) -> dict[str, object]:
    options = workshop.client.post("/v1/auth/step-up/passkey", headers=headers)
    assert options.status_code == 200, options.text
    confirmed = workshop.client.post(
        "/v1/auth/step-up/passkey/verify",
        json={
            "passkey_challenge_id": options.json()["passkey_challenge_id"],
            "credential": authenticator.sign(options.json()["options"]),
        },
        headers=headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    return dict(confirmed.json())


def test_a_passkey_raising_a_session_hands_a_ticket_and_it_rotates(
    workshop: Workshop,
) -> None:
    authenticator = new_authenticator()
    token, _ = sign_up_with_passkey(workshop, authenticator)
    me = workshop.client.get("/v1/me", headers=bearer(token)).json()
    one_factor = store_session(
        workshop,
        str(me["user"]["id"]),
        str(generate_access_token()),
        AuthLevel.ONE_FACTOR,
    )

    confirmed = confirm_with_passkey(workshop, authenticator, one_factor)
    still_one = workshop.client.get("/v1/me/security", headers=one_factor).json()
    rotated = workshop.client.post(
        ROTATE_PATH,
        json={"rotation_ticket": confirmed["rotation_ticket"]},
        headers=one_factor,
    )

    assert (confirmed["auth_level"], confirmed["is_level_raised"]) == (
        "two_factor",
        True,
    )
    assert still_one["auth_level"] == "one_factor"
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["auth_level"] == "two_factor"
    after = workshop.client.get("/v1/me/security", headers=one_factor).json()
    assert (after["auth_level"], after["authenticated_at"]) == ("one_factor", None)


def test_a_two_factor_session_raises_nothing(workshop: Workshop) -> None:
    authenticator = new_authenticator()
    token, _ = sign_up_with_passkey(workshop, authenticator)
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    confirmed = confirm_with_passkey(workshop, authenticator, bearer(token))

    assert (
        confirmed["auth_level"],
        confirmed["is_level_raised"],
        confirmed["rotation_ticket"],
    ) == ("two_factor", False, None)
