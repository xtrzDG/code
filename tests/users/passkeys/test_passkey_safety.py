"""
What keeps passkeys safe over the real API: a copied authenticator is
caught by its signature counter and the passkey is suspended, a passkey
confirms sensitive actions (step-up), a platform admin may enrol one at the
first sign-in, and a server without a relying party offers none.
"""

from collections.abc import Iterator

import pytest

from app.schemas.constants.compliance import AuditAction
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL, E2E_ENVIRONMENT
from tests.users.mfa.mfa_api import (
    STEP_UP_SECONDS,
    login_code_step,
    reason_codes,
    second_step,
)
from tests.users.passkeys.passkey_api import (
    OWNER_EMAIL,
    audit_entries,
    new_authenticator,
    passkey_options,
    sign_in_with_passkey,
    sign_up_with_passkey,
)

ADMIN_CLIENTS_URL: str = "/v1/admin/clients"


def test_a_copied_authenticator_suspends_the_passkey(workshop: Workshop) -> None:
    original = new_authenticator()
    token, added = sign_up_with_passkey(workshop, original)
    me = workshop.client.get("/v1/me", headers=bearer(token)).json()
    owner_id: str = me["user"]["id"]
    copy = original.copy()

    first = sign_in_with_passkey(workshop, original)
    # The copy signs with the counter the original already used.
    copied = sign_in_with_passkey(workshop, copy)
    step = login_code_step(workshop, OWNER_EMAIL)
    afterwards = passkey_options(workshop, step)
    listed = workshop.client.get("/v1/me/passkeys", headers=bearer(token))

    assert first.status_code == 200, first.text
    assert copied.status_code == 422
    assert reason_codes(copied) == ["passkey_clone_suspected"]
    # The suspended passkey is no longer offered; recovery codes still are.
    assert step["mfa_challenge"]["methods"] == ["recovery_code"]
    assert afterwards.status_code == 409
    assert reason_codes(afterwards) == ["passkeys_unavailable"]
    assert listed.json()["items"][0]["clone_suspected_at"] is not None
    assert f"{added['passkey']['id']}:clone_suspected" in [
        str(entry.entity_id)
        for entry in audit_entries(workshop, owner_id)
        if entry.action is AuditAction.MFA_CHANGED
    ]
    recovered = second_step(workshop, step, recovery_code=added["recovery_codes"][0])
    assert recovered.status_code == 200, recovered.text


def test_a_passkey_confirms_a_sensitive_action(workshop: Workshop) -> None:
    authenticator = new_authenticator()
    token, _ = sign_up_with_passkey(workshop, authenticator)
    workshop.clock.advance(STEP_UP_SECONDS + 1)
    refused = workshop.client.post(
        "/v1/me/passkeys/registration", headers=bearer(token)
    )

    options = workshop.client.post("/v1/auth/step-up/passkey", headers=bearer(token))
    confirmed = workshop.client.post(
        "/v1/auth/step-up/passkey/verify",
        json={
            "passkey_challenge_id": options.json()["passkey_challenge_id"],
            "credential": authenticator.sign(options.json()["options"]),
        },
        headers=bearer(token),
    )
    allowed = workshop.client.post(
        "/v1/me/passkeys/registration", headers=bearer(token)
    )

    assert reason_codes(refused) == ["step_up_required"]
    assert options.status_code == 200, options.text
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["auth_level"] == "two_factor"
    assert allowed.status_code == 200, allowed.text


def test_a_step_up_answer_counts_once(workshop: Workshop) -> None:
    authenticator = new_authenticator()
    token, _ = sign_up_with_passkey(workshop, authenticator)
    options = workshop.client.post("/v1/auth/step-up/passkey", headers=bearer(token))
    body = {
        "passkey_challenge_id": options.json()["passkey_challenge_id"],
        "credential": authenticator.sign(options.json()["options"]),
    }

    first = workshop.client.post(
        "/v1/auth/step-up/passkey/verify", json=body, headers=bearer(token)
    )
    replayed = workshop.client.post(
        "/v1/auth/step-up/passkey/verify", json=body, headers=bearer(token)
    )

    assert first.status_code == 200, first.text
    assert replayed.status_code == 422
    assert reason_codes(replayed) == ["passkey_rejected"]


def test_an_admin_enrols_a_passkey_at_the_first_sign_in(workshop: Workshop) -> None:
    authenticator = new_authenticator()
    step = login_code_step(workshop, ADMIN_EMAIL)
    challenge_id: str = step["mfa_challenge"]["mfa_challenge_id"]

    options = workshop.client.post(
        "/v1/auth/mfa/passkey/enroll", json={"mfa_challenge_id": challenge_id}
    )
    finished = workshop.client.post(
        "/v1/auth/mfa/passkey/enroll/finish",
        json={
            "mfa_challenge_id": challenge_id,
            "passkey_challenge_id": options.json()["passkey_challenge_id"],
            "credential": authenticator.register(options.json()["options"]),
            "name": "Admin key",
        },
    )
    clients = workshop.client.get(
        ADMIN_CLIENTS_URL, headers=bearer(finished.json()["access_token"])
    )
    next_step = login_code_step(workshop, ADMIN_EMAIL)

    assert step["mfa_challenge"]["requires_enrollment"] is True
    assert step["mfa_challenge"]["enrollment_methods"] == ["passkey", "totp"]
    assert options.status_code == 200, options.text
    assert finished.status_code == 200, finished.text
    assert finished.json()["auth_level"] == "two_factor"
    assert len(finished.json()["recovery_codes"]) == 10
    assert clients.status_code == 200, clients.text
    assert next_step["mfa_challenge"]["requires_enrollment"] is False
    assert next_step["mfa_challenge"]["methods"][0] == "passkey"


@pytest.fixture
def workshop_by_address() -> Iterator[Workshop]:
    """A cabinet reached by an IP address: passkeys need a domain name."""

    opened = start_workshop(
        {**E2E_ENVIRONMENT, "CABINET_BASE_URL": "http://127.0.0.1:4102"}
    )
    with opened.client:
        yield opened


def test_without_a_domain_name_no_passkey_is_offered(
    workshop_by_address: Workshop,
) -> None:
    workshop = workshop_by_address
    token, _ = workshop.sign_in_with_email(OWNER_EMAIL)

    listed = workshop.client.get("/v1/me/passkeys", headers=bearer(token))
    started = workshop.client.post(
        "/v1/me/passkeys/registration", headers=bearer(token)
    )
    admin_step = login_code_step(workshop, ADMIN_EMAIL)

    assert listed.status_code == 200, listed.text
    assert listed.json()["is_available"] is False
    assert started.status_code == 409
    assert reason_codes(started) == ["passkeys_unavailable"]
    assert admin_step["mfa_challenge"]["enrollment_methods"] == ["totp"]
