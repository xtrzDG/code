"""
A person whose second factor is a passkey confirms sensitive actions with
it or with a recovery code, never with a login code alone: a stolen
session with access to the mailbox or phone must not reach the
second-factor changes (removing the passkey, adding its own). A login code
alone does not plant an authenticator on such an account either, and
asking for the options of a new passkey is limited per person.
"""

from httpx2 import Response

from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import JsonObject
from tests.users.mfa.mfa_api import (
    RESEND_WAIT_SECONDS,
    STEP_UP_SECONDS,
    login_code_step,
    reason_codes,
)
from tests.users.passkeys.passkey_api import (
    OWNER_EMAIL,
    new_authenticator,
    sign_in_with_passkey,
    sign_up_with_passkey,
)

REGISTRATION_URL: str = "/v1/me/passkeys/registration"


def own_login_code(workshop: Workshop) -> JsonObject:
    """A login code at the owner's own e-mail, as the sign-in sends it."""

    workshop.clock.advance(RESEND_WAIT_SECONDS)
    started = workshop.client.post("/v1/auth/otp/start", json={"email": OWNER_EMAIL})
    assert started.status_code == 200, started.text
    return {
        "challenge_id": started.json()["challenge_id"],
        "login_code": str(workshop.otp.codes[-1].code),
    }


def first_passkey_id(workshop: Workshop, token: str) -> str:
    listed = workshop.client.get("/v1/me/passkeys", headers=bearer(token))
    passkey_id: str = listed.json()["items"][0]["id"]
    return passkey_id


def step_up(workshop: Workshop, token: str, body: JsonObject) -> Response:
    return workshop.client.post(
        "/v1/auth/step-up/verify", json=body, headers=bearer(token)
    )


def test_a_login_code_does_not_confirm_a_passkey_person(workshop: Workshop) -> None:
    token, _ = sign_up_with_passkey(workshop, new_authenticator())
    workshop.clock.advance(STEP_UP_SECONDS + 1)
    codes_before = len(workshop.otp.codes)

    started = workshop.client.post(
        "/v1/auth/step-up", json={"method": "login_code"}, headers=bearer(token)
    )
    codes_sent = len(workshop.otp.codes) - codes_before
    refused = step_up(workshop, token, own_login_code(workshop))
    removed = workshop.client.delete(
        f"/v1/me/passkeys/{first_passkey_id(workshop, token)}", headers=bearer(token)
    )
    security = workshop.client.get("/v1/me/security", headers=bearer(token)).json()

    assert started.status_code == 200, started.text
    assert started.json()["method"] == "passkey"
    assert started.json()["login_code"] is None
    assert codes_sent == 0
    assert refused.status_code == 422
    assert reason_codes(removed) == ["step_up_required"]
    assert security["passkey_count"] == 1


def test_a_recovery_code_confirms_a_passkey_person(workshop: Workshop) -> None:
    token, added = sign_up_with_passkey(workshop, new_authenticator())
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    confirmed = step_up(workshop, token, {"recovery_code": added["recovery_codes"][0]})
    reused = step_up(workshop, token, {"recovery_code": added["recovery_codes"][0]})
    security = workshop.client.get("/v1/me/security", headers=bearer(token)).json()

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["auth_level"] == "two_factor"
    assert reused.status_code == 422
    assert security["auth_level"] == "two_factor"
    assert security["recovery_codes_left"] == 9


def test_a_suspended_passkey_leaves_the_recovery_codes(workshop: Workshop) -> None:
    original = new_authenticator()
    token, added = sign_up_with_passkey(workshop, original)
    copy = original.copy()
    assert sign_in_with_passkey(workshop, original).status_code == 200
    # The copy signs with the counter the original already used.
    assert sign_in_with_passkey(workshop, copy).status_code == 422
    workshop.clock.advance(STEP_UP_SECONDS + 1)
    codes_before = len(workshop.otp.codes)

    started = workshop.client.post("/v1/auth/step-up", headers=bearer(token))
    codes_sent = len(workshop.otp.codes) - codes_before
    refused = step_up(workshop, token, own_login_code(workshop))
    confirmed = step_up(workshop, token, {"recovery_code": added["recovery_codes"][1]})

    assert started.json()["method"] == "recovery_code"
    assert started.json()["passkey_available"] is False
    assert codes_sent == 0
    assert refused.status_code == 422
    assert confirmed.status_code == 200, confirmed.text


def test_a_login_code_plants_no_authenticator_on_a_passkey_person(
    workshop: Workshop,
) -> None:
    token, _ = sign_up_with_passkey(workshop, new_authenticator())
    step = login_code_step(workshop, OWNER_EMAIL)

    enrolled = workshop.client.post(
        "/v1/auth/mfa/enroll",
        json={"mfa_challenge_id": step["mfa_challenge"]["mfa_challenge_id"]},
    )
    security = workshop.client.get("/v1/me/security", headers=bearer(token)).json()

    assert step["mfa_challenge"]["requires_enrollment"] is False
    assert enrolled.status_code == 409
    assert "secret" not in enrolled.json()
    assert security["totp_status"] is None


def test_asking_for_new_passkey_options_is_limited(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_email(OWNER_EMAIL)

    answers = [
        workshop.client.post(REGISTRATION_URL, headers=bearer(token)) for _ in range(11)
    ]

    assert [answer.status_code for answer in answers[:10]] == [200] * 10
    assert answers[10].status_code == 429
    assert int(answers[10].headers["Retry-After"]) > 0
