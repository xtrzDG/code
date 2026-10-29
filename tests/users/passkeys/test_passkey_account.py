"""
Account → Security: adding, naming and removing passkeys. The first one
turns two-factor sign-in on (recovery codes once, other sessions end);
removing the last one turns it off again, everywhere.
"""

from tests.e2e.harness import Workshop, bearer
from tests.users.mfa.mfa_api import RESEND_WAIT_SECONDS, reason_codes
from tests.users.passkeys.passkey_api import (
    OWNER_EMAIL,
    add_passkey,
    mfa_change_references,
    new_authenticator,
    sign_up_with_passkey,
)

STEP_UP_SECONDS: int = 600


def test_a_first_passkey_turns_on_two_factor_sign_in(workshop: Workshop) -> None:
    other_token, _ = workshop.sign_in_with_email(OWNER_EMAIL)
    workshop.clock.advance(RESEND_WAIT_SECONDS)
    token, session = workshop.sign_in_with_email(OWNER_EMAIL)
    authenticator = new_authenticator()

    added = add_passkey(workshop, token, authenticator)
    security = workshop.client.get("/v1/me/security", headers=bearer(token))
    listed = workshop.client.get("/v1/me/passkeys", headers=bearer(token))
    other = workshop.client.get("/v1/me", headers=bearer(other_token))

    assert added.status_code == 201, added.text
    passkey = added.json()["passkey"]
    assert passkey["name"] == "Passkey"
    assert passkey["transports"] == ["internal", "hybrid"]
    assert passkey["clone_suspected_at"] is None
    assert len(added.json()["recovery_codes"]) == 10
    assert security.json()["passkey_count"] == 1
    assert security.json()["auth_level"] == "two_factor"
    assert security.json()["recovery_codes_left"] == 10
    assert [item["id"] for item in listed.json()["items"]] == [passkey["id"]]
    assert listed.json()["is_available"] is True
    assert listed.json()["is_recommended"] is False
    # The session signed in before the passkey existed ends.
    assert other.status_code == 401
    assert mfa_change_references(workshop, session["user"]["id"]) == [
        session["user"]["id"]
    ]


def test_another_passkey_keeps_the_codes_and_the_other_sessions(
    workshop: Workshop,
) -> None:
    token, first = sign_up_with_passkey(workshop, new_authenticator())
    workshop.clock.advance(60)

    added = add_passkey(workshop, token, new_authenticator(), name="Work laptop")
    listed = workshop.client.get("/v1/me/passkeys", headers=bearer(token))

    assert added.status_code == 201, added.text
    assert added.json()["recovery_codes"] == []
    assert added.json()["passkey"]["name"] == "Work laptop"
    # Newest first.
    assert [item["name"] for item in listed.json()["items"]] == [
        "Work laptop",
        first["passkey"]["name"],
    ]


def test_adding_a_passkey_needs_a_fresh_confirmation(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_email(OWNER_EMAIL)
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    started = workshop.client.post(
        "/v1/me/passkeys/registration", headers=bearer(token)
    )

    assert started.status_code == 401
    assert reason_codes(started) == ["step_up_required"]


def test_one_authenticator_is_added_once(workshop: Workshop) -> None:
    authenticator = new_authenticator()
    token, first = sign_up_with_passkey(workshop, authenticator)

    started = workshop.client.post(
        "/v1/me/passkeys/registration", headers=bearer(token)
    )
    excluded = [item["id"] for item in started.json()["options"]["exclude_credentials"]]
    again = workshop.client.post(
        "/v1/me/passkeys",
        json={
            "passkey_challenge_id": started.json()["passkey_challenge_id"],
            "credential": authenticator.register(started.json()["options"]),
        },
        headers=bearer(token),
    )

    assert excluded == [authenticator.credential_id_text]
    assert again.status_code == 409
    assert (
        len(
            workshop.client.get("/v1/me/passkeys", headers=bearer(token)).json()[
                "items"
            ]
        )
        == 1
    )
    assert first["passkey"]["id"]


def test_a_new_passkey_from_another_site_or_an_old_challenge_is_refused(
    workshop: Workshop,
) -> None:
    token, _ = workshop.sign_in_with_email(OWNER_EMAIL)
    authenticator = new_authenticator()
    started = workshop.client.post(
        "/v1/me/passkeys/registration", headers=bearer(token)
    )
    body = {
        "passkey_challenge_id": started.json()["passkey_challenge_id"],
        "credential": authenticator.register(
            started.json()["options"], origin="https://phishing.example"
        ),
    }

    phished = workshop.client.post("/v1/me/passkeys", json=body, headers=bearer(token))
    body["credential"] = authenticator.register(started.json()["options"])
    reused = workshop.client.post("/v1/me/passkeys", json=body, headers=bearer(token))

    assert phished.status_code == 422
    assert reason_codes(phished) == ["passkey_rejected"]
    # The challenge was taken by the first answer, whatever it said.
    assert reused.status_code == 422
    assert reason_codes(reused) == ["passkey_rejected"]


def test_a_passkey_is_renamed_and_removed_by_its_person_only(
    workshop: Workshop,
) -> None:
    token, added = sign_up_with_passkey(workshop, new_authenticator())
    passkey_id = added["passkey"]["id"]
    stranger, _ = workshop.sign_in_with_email("stranger@cafe.example")

    renamed = workshop.client.patch(
        f"/v1/me/passkeys/{passkey_id}",
        json={"name": "Phone"},
        headers=bearer(token),
    )
    foreign = workshop.client.delete(
        f"/v1/me/passkeys/{passkey_id}", headers=bearer(stranger)
    )
    unknown = workshop.client.delete("/v1/me/passkeys/nonsense", headers=bearer(token))
    removed = workshop.client.delete(
        f"/v1/me/passkeys/{passkey_id}", headers=bearer(token)
    )
    security = workshop.client.get("/v1/me/security", headers=bearer(token))

    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Phone"
    assert foreign.status_code == 404
    assert unknown.status_code == 404
    assert removed.status_code == 204
    # The last second factor is gone: codes too, and every session counts as
    # one factor again.
    assert security.json()["passkey_count"] == 0
    assert security.json()["recovery_codes_left"] == 0
    assert security.json()["auth_level"] == "one_factor"
