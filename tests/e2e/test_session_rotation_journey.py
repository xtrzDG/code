"""
POST /v1/auth/session/rotate on the real application: setting up an
authenticator raises the one-factor session, and the answer's one-time
rotation ticket swaps its token (same person and end, two factors); the
old token stays one factor and ends 30 seconds later. Without the ticket,
with a used one, or for a session that proved nothing, the session keeps
its token (422 without a body, 409 otherwise).
"""

from collections.abc import Iterator

import pytest

from app.schemas.typings.mfa.constrained_strings import TotpSecret
from tests.e2e.harness import Workshop, bearer, start_workshop

OWNER_PHONE: str = "+995 555 98 76 54"
ROTATE_PATH: str = "/v1/auth/session/rotate"


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    opened = start_workshop()
    with opened.client:
        yield opened


def turn_on_authenticator(workshop: Workshop, token: str) -> dict[str, object]:
    started = workshop.client.post("/v1/me/mfa/totp", headers=bearer(token))
    assert started.status_code == 200, started.text
    workshop.authenticators.secrets[OWNER_PHONE] = TotpSecret(
        str(started.json()["secret"])
    )
    confirmed = workshop.client.post(
        "/v1/me/mfa/totp/confirm",
        json={"code": workshop.authenticators.code_for(OWNER_PHONE, workshop.clock)},
        headers=bearer(token),
    )
    assert confirmed.status_code == 200, confirmed.text
    return dict(confirmed.json())


def test_a_new_authenticator_swaps_the_token_and_the_old_one_ends(
    workshop: Workshop,
) -> None:
    token, session = workshop.sign_in_with_phone(OWNER_PHONE)

    turned_on = turn_on_authenticator(workshop, token)
    before_swap = workshop.client.get("/v1/me/security", headers=bearer(token))
    rotated = workshop.client.post(
        ROTATE_PATH,
        json={"rotation_ticket": turned_on["rotation_ticket"]},
        headers=bearer(token),
    )

    assert turned_on["is_level_raised"] is True
    assert before_swap.json()["auth_level"] == "one_factor"
    assert rotated.status_code == 200, rotated.text
    body = rotated.json()
    assert body["access_token"] != token
    assert body["user"]["id"] == session["user"]["id"]
    assert (body["expires_at"], body["auth_level"], body["is_new_user"]) == (
        session["expires_at"],
        "two_factor",
        False,
    )
    fresh = bearer(str(body["access_token"]))
    assert workshop.client.get("/v1/me/security", headers=bearer(token)).json()[
        "auth_level"
    ] == ("one_factor")
    workshop.clock.advance(31)
    assert workshop.client.get("/v1/me", headers=bearer(token)).status_code == 401
    me = workshop.client.get("/v1/me/security", headers=fresh)
    assert me.status_code == 200, me.text
    assert me.json()["auth_level"] == "two_factor"


def test_a_session_without_a_ticket_keeps_its_token(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER_PHONE)

    without_body = workshop.client.post(ROTATE_PATH, headers=bearer(token))
    without_ticket = workshop.client.post(
        ROTATE_PATH,
        json={"rotation_ticket": "x" * 43},
        headers=bearer(token),
    )

    assert without_body.status_code == 422, without_body.text
    assert without_ticket.status_code == 409, without_ticket.text
    assert workshop.client.get("/v1/me", headers=bearer(token)).status_code == 200
