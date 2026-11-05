"""
A passkey answers the second step of a sign-in: offered first, checked
against the step, the cabinet's origin and the stored key, used once.
"""

from app.schemas.constants.compliance import AuditAction, AuditSecurityEvent
from tests.e2e.harness import Workshop, bearer
from tests.users.mfa.mfa_api import login_code_step, reason_codes, second_step
from tests.users.passkeys.passkey_api import (
    OWNER_EMAIL,
    add_passkey,
    answer_with_passkey,
    audit_entries,
    new_authenticator,
    passkey_options,
    sign_in_with_passkey,
    sign_up_with_passkey,
)


def test_the_second_step_offers_the_passkey_first(workshop: Workshop) -> None:
    sign_up_with_passkey(workshop, new_authenticator())

    step = login_code_step(workshop, OWNER_EMAIL)

    assert step["mfa_required"] is True
    assert step["mfa_challenge"]["methods"] == ["passkey", "recovery_code"]
    assert step["mfa_challenge"]["requires_enrollment"] is False
    assert step["mfa_challenge"]["enrollment_methods"] == []
    assert "access_token" not in step


def test_a_passkey_answer_opens_a_two_factor_session(workshop: Workshop) -> None:
    authenticator = new_authenticator()
    _, added = sign_up_with_passkey(workshop, authenticator)

    signed_in = sign_in_with_passkey(workshop, authenticator)
    token = signed_in.json()["access_token"]
    me = workshop.client.get("/v1/me", headers=bearer(token))
    listed = workshop.client.get("/v1/me/passkeys", headers=bearer(token))

    assert signed_in.status_code == 200, signed_in.text
    assert signed_in.json()["auth_level"] == "two_factor"
    assert signed_in.json()["recovery_codes"] == []
    assert me.json()["auth_level"] == "two_factor"
    assert listed.json()["items"][0]["last_used_at"] is not None
    assert added["passkey"]["last_used_at"] is None


def test_the_options_allow_only_the_persons_own_passkeys(workshop: Workshop) -> None:
    authenticator = new_authenticator()
    sign_up_with_passkey(workshop, authenticator)
    sign_up_with_passkey(workshop, new_authenticator(), "another@cafe.example")

    options = passkey_options(workshop, login_code_step(workshop, OWNER_EMAIL))

    assert options.status_code == 200, options.text
    assert options.json()["options"]["rp_id"] == "cabinet.workshop.example"
    assert [item["id"] for item in options.json()["options"]["allow_credentials"]] == [
        authenticator.credential_id_text
    ]


def test_an_answer_from_another_site_is_refused_and_counted(
    workshop: Workshop,
) -> None:
    authenticator = new_authenticator()
    token, session = workshop.sign_in_with_email(OWNER_EMAIL)
    assert add_passkey(workshop, token, authenticator).status_code == 201
    step = login_code_step(workshop, OWNER_EMAIL)

    phished = answer_with_passkey(
        workshop, step, authenticator, origin="https://cabinet.workshop.example.evil"
    )
    login_events = [
        entry.security_event
        for entry in audit_entries(workshop, session["user"]["id"])
        if entry.action is AuditAction.LOGIN
    ]

    assert phished.status_code == 422
    assert reason_codes(phished) == ["passkey_rejected"]
    # The first sign-in, then the refused answer.
    assert login_events == [None, AuditSecurityEvent.LOGIN_FAILED]


def test_five_refused_answers_lock_the_step(workshop: Workshop) -> None:
    authenticator = new_authenticator()
    sign_up_with_passkey(workshop, authenticator)
    step = login_code_step(workshop, OWNER_EMAIL)

    answers = [
        answer_with_passkey(
            workshop, step, authenticator, origin="https://evil.example"
        )
        for _ in range(5)
    ]
    locked = passkey_options(workshop, step)

    assert [answer.status_code for answer in answers] == [422] * 5
    assert locked.status_code == 429


def test_a_passkey_challenge_answers_only_its_own_step(workshop: Workshop) -> None:
    authenticator = new_authenticator()
    sign_up_with_passkey(workshop, authenticator)
    first = login_code_step(workshop, OWNER_EMAIL)
    options = passkey_options(workshop, first)
    second = login_code_step(workshop, OWNER_EMAIL)

    crossed = workshop.client.post(
        "/v1/auth/mfa/passkey/verify",
        json={
            "mfa_challenge_id": second["mfa_challenge"]["mfa_challenge_id"],
            "passkey_challenge_id": options.json()["passkey_challenge_id"],
            "credential": authenticator.sign(options.json()["options"]),
        },
    )

    assert crossed.status_code == 422
    assert reason_codes(crossed) == ["passkey_rejected"]


def test_a_synced_passkey_without_a_counter_signs_in_again_and_again(
    workshop: Workshop,
) -> None:
    authenticator = new_authenticator(counts_signatures=False)
    sign_up_with_passkey(workshop, authenticator)

    answers = [sign_in_with_passkey(workshop, authenticator) for _ in range(3)]

    assert [answer.status_code for answer in answers] == [200, 200, 200]
    assert authenticator.sign_count == 0


def test_a_passkey_person_may_still_use_a_recovery_code(workshop: Workshop) -> None:
    _, added = sign_up_with_passkey(workshop, new_authenticator())
    step = login_code_step(workshop, OWNER_EMAIL)

    recovered = second_step(workshop, step, recovery_code=added["recovery_codes"][0])
    with_app_code = second_step(
        workshop, login_code_step(workshop, OWNER_EMAIL), code="123456"
    )

    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["auth_level"] == "two_factor"
    # No authenticator app: an app code is simply wrong.
    assert with_app_code.status_code == 422
    assert reason_codes(with_app_code) == ["wrong_code"]
