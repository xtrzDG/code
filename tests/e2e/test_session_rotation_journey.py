"""
POST /v1/auth/session/rotate on the real application: a session that just
proved itself gets a new token (same person, level and end), the old token
ends 30 seconds later, and a session whose proof is older than the step-up
window keeps its token (409).
"""

from collections.abc import Iterator

import pytest

from tests.e2e.harness import Workshop, bearer, start_workshop

OWNER_PHONE: str = "+995 555 98 76 54"
ROTATE_PATH: str = "/v1/auth/session/rotate"


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    opened = start_workshop()
    with opened.client:
        yield opened


def test_a_fresh_session_rotates_and_its_old_token_ends(workshop: Workshop) -> None:
    token, session = workshop.sign_in_with_phone(OWNER_PHONE)

    rotated = workshop.client.post(ROTATE_PATH, headers=bearer(token))

    assert rotated.status_code == 200, rotated.text
    body = rotated.json()
    assert body["access_token"] != token
    assert body["user"]["id"] == session["user"]["id"]
    assert (body["expires_at"], body["auth_level"], body["is_new_user"]) == (
        session["expires_at"],
        session["auth_level"],
        False,
    )
    workshop.clock.advance(31)
    assert workshop.client.get("/v1/me", headers=bearer(token)).status_code == 401
    me = workshop.client.get("/v1/me", headers=bearer(str(body["access_token"])))
    assert me.status_code == 200, me.text


def test_a_session_without_a_recent_proof_keeps_its_token(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER_PHONE)
    workshop.clock.advance(60 * 60)

    refused = workshop.client.post(ROTATE_PATH, headers=bearer(token))

    assert refused.status_code == 409, refused.text
    assert workshop.client.get("/v1/me", headers=bearer(token)).status_code == 200
