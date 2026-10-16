"""
Step-up: sensitive actions need a sign-in or a fresh confirmation within
STEP_UP_MAX_AGE_SECONDS (ten minutes). A refusal is 401 with the reason
`step_up_required` and a WWW-Authenticate challenge; the session stays
valid. People confirm with an authenticator code or, without one, with a
login code sent to their own phone or e-mail.
"""

from typing import Any

from httpx2 import Response

from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.users.prefixed_id import UserId
from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, sign_in_and_create_restaurant
from tests.users.mfa.mfa_api import (
    STEP_UP_SECONDS,
    reason_codes,
    set_up_authenticator,
    wrong_code_for,
)

STAFF: dict[str, str] = {"phone_number": "+995 555 77 88 99", "role": "staff"}


def invite(workshop: Workshop, business_id: str, token: str) -> Response:
    return workshop.client.post(
        f"/v1/businesses/{business_id}/members", json=STAFF, headers=bearer(token)
    )


def assert_step_up_required(response: Response) -> None:
    assert response.status_code == 401, response.text
    assert response.json()["error"] == "authentication_required"
    assert reason_codes(response) == ["step_up_required"]
    assert response.json()["reasons"][0]["details"] == [str(STEP_UP_SECONDS)]
    assert (
        'error="insufficient_user_authentication"'
        in response.headers["WWW-Authenticate"]
    )


def test_a_sensitive_action_needs_a_recent_sign_in(workshop: Workshop) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    refused = invite(workshop, business_id, token)
    me = workshop.client.get("/v1/me", headers=bearer(token))

    assert_step_up_required(refused)
    assert me.status_code == 200


def test_a_login_code_confirms_a_person_without_an_authenticator(
    workshop: Workshop,
) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    started = workshop.client.post("/v1/auth/step-up", headers=bearer(token))
    challenge_id: str = started.json()["login_code"]["challenge_id"]
    code: str = str(workshop.otp.codes[-1].code)
    wrong = workshop.client.post(
        "/v1/auth/step-up/verify",
        json={"challenge_id": challenge_id, "login_code": wrong_code_for(code)},
        headers=bearer(token),
    )
    confirmed = workshop.client.post(
        "/v1/auth/step-up/verify",
        json={"challenge_id": challenge_id, "login_code": code},
        headers=bearer(token),
    )

    assert started.status_code == 200, started.text
    assert started.json()["method"] == "login_code"
    assert workshop.otp.codes[-1].phone_number == "+995555123456"
    assert wrong.status_code == 422
    assert reason_codes(wrong) == ["wrong_code"]
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["auth_level"] == "one_factor"
    assert invite(workshop, business_id, token).status_code == 201


def test_an_authenticator_confirms_and_the_confirmation_expires(
    workshop: Workshop,
) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    set_up_authenticator(workshop, token, GEORGIAN_OWNER_PHONE)
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    started = workshop.client.post("/v1/auth/step-up", headers=bearer(token))
    code = workshop.authenticators.code_for(GEORGIAN_OWNER_PHONE, workshop.clock)
    confirmed = workshop.client.post(
        "/v1/auth/step-up/verify", json={"code": code}, headers=bearer(token)
    )
    allowed = invite(workshop, business_id, token)
    workshop.clock.advance(STEP_UP_SECONDS + 1)
    expired = workshop.client.patch(
        f"/v1/businesses/{business_id}/members/{allowed.json()['members'][1]['user_id']}",
        json={"role": "owner"},
        headers=bearer(token),
    )

    assert started.json() == {"method": "totp", "login_code": None}
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["auth_level"] == "two_factor"
    assert confirmed.json()["step_up_valid_until"] == (
        confirmed.json()["authenticated_at"] + STEP_UP_SECONDS * 1_000_000
    )
    assert allowed.status_code == 201, allowed.text
    assert_step_up_required(expired)


SUPPORT_REASON: dict[str, Any] = {"reason": "Owner asked why bookings stopped"}
NEW_ADMIN: dict[str, Any] = {"email": "ops@example.com", "role": "billing"}


def test_every_sensitive_action_asks_to_confirm(workshop: Workshop) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    workshop.clock.advance(STEP_UP_SECONDS + 1)
    base: str = f"/v1/businesses/{business_id}"
    contact: str = f"{base}/contacts/{ContactId()}"
    member: str = f"{base}/members/{UserId()}"
    owner, admin = bearer(token), bearer(admin_token)
    calls: list[tuple[str, str, dict[str, str], dict[str, Any] | None]] = [
        ("GET", f"{contact}/export", owner, None),
        ("DELETE", contact, owner, None),
        ("POST", f"{base}/members", owner, STAFF),
        ("PATCH", member, owner, {"role": "staff"}),
        ("DELETE", member, owner, None),
        ("PUT", f"{base}/channels/telegram", owner, {"bot_token": "1:token-0000"}),
        ("PUT", f"{base}/security", owner, {"require_mfa_for_members": False}),
        ("POST", "/v1/me/mfa/totp", owner, None),
        ("POST", f"/v1/admin/clients/{business_id}/open", admin, SUPPORT_REASON),
        (
            "POST",
            "/v1/admin/team",
            admin,
            {"email": "ops@example.com", "role": "billing"},
        ),
        ("POST", "/v1/admin/security/encryption-keys/rotate", admin, None),
    ]

    for method, url, headers, body in calls:
        response = workshop.client.request(method, url, headers=headers, json=body)
        assert_step_up_required(response)


def test_the_website_chat_needs_no_confirmation(workshop: Workshop) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    # No outside account's credentials: changing its look is everyday work.
    saved = workshop.client.put(
        f"/v1/businesses/{business_id}/channels/web",
        json={"widget_color": "#0F766E"},
        headers=bearer(token),
    )

    assert saved.status_code == 200, saved.text
    assert saved.json()["widget_color"] == "#0F766E"
