"""
Account → Security: setting up an authenticator (the session becomes
two-factor), recovery codes shown once and regenerated, removing the
authenticator; every change is in the audit log as MFA_CHANGED.
"""

from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE
from tests.users.mfa.mfa_api import (
    login_code_step,
    mfa_changes,
    reason_codes,
    second_step,
    set_up_authenticator,
    wrong_code_for,
)

OWNER: str = GEORGIAN_OWNER_PHONE
SECURITY_URL: str = "/v1/me/security"


def test_setting_up_an_authenticator_makes_the_session_two_factor(
    workshop: Workshop,
) -> None:
    token, session = workshop.sign_in_with_phone(OWNER)
    headers = bearer(token)
    before = workshop.client.get(SECURITY_URL, headers=headers).json()

    started = workshop.client.post("/v1/me/mfa/totp", headers=headers)
    secret: str = started.json()["secret"]
    workshop.authenticators.secrets[OWNER] = secret
    code: str = workshop.authenticators.code_for(OWNER, workshop.clock)
    wrong = workshop.client.post(
        "/v1/me/mfa/totp/confirm", json={"code": wrong_code_for(code)}, headers=headers
    )
    pending = workshop.client.get(SECURITY_URL, headers=headers).json()
    confirmed = workshop.client.post(
        "/v1/me/mfa/totp/confirm", json={"code": code}, headers=headers
    )
    after = workshop.client.get(SECURITY_URL, headers=headers).json()
    again = workshop.client.post("/v1/me/mfa/totp", headers=headers)

    assert before["totp_status"] is None
    assert before["recovery_codes_left"] == 0
    assert before["auth_level"] == "one_factor"
    assert before["step_up_max_age_seconds"] == 600
    assert before["is_mfa_required"] is False
    assert started.status_code == 200, started.text
    assert started.json()["provisioning_uri"].endswith(
        f"?secret={secret}&issuer=Assistant%20Workshop"
    )
    assert wrong.status_code == 422
    assert reason_codes(wrong) == ["wrong_code"]
    assert pending["totp_status"] == "pending"
    assert confirmed.status_code == 200, confirmed.text
    assert len(confirmed.json()["recovery_codes"]) == 10
    assert after["totp_status"] == "active"
    assert after["totp_confirmed_at"] is not None
    assert after["recovery_codes_left"] == 10
    assert after["auth_level"] == "two_factor"
    assert again.status_code == 409
    assert mfa_changes(workshop, session["user"]["id"]) == ["totp_factor"]


def test_new_recovery_codes_replace_the_old_ones(workshop: Workshop) -> None:
    token, session = workshop.sign_in_with_phone(OWNER)
    old_codes = set_up_authenticator(workshop, token, OWNER)

    renewed = workshop.client.post("/v1/me/mfa/recovery-codes", headers=bearer(token))
    new_codes: list[str] = renewed.json()["recovery_codes"]
    old_refused = second_step(
        workshop, login_code_step(workshop, OWNER), recovery_code=old_codes[0]
    )
    new_accepted = second_step(
        workshop, login_code_step(workshop, OWNER), recovery_code=new_codes[0]
    )

    assert renewed.status_code == 200, renewed.text
    assert len(new_codes) == 10 and not set(new_codes) & set(old_codes)
    assert old_refused.status_code == 422
    assert new_accepted.status_code == 200, new_accepted.text
    assert mfa_changes(workshop, session["user"]["id"]) == [
        "totp_factor",
        "recovery_codes",
    ]


def test_removing_the_authenticator_ends_the_second_step(workshop: Workshop) -> None:
    token, session = workshop.sign_in_with_phone(OWNER)
    set_up_authenticator(workshop, token, OWNER)
    headers = bearer(token)

    removed = workshop.client.delete("/v1/me/mfa/totp", headers=headers)
    security = workshop.client.get(SECURITY_URL, headers=headers).json()
    removed_again = workshop.client.delete("/v1/me/mfa/totp", headers=headers)
    no_codes = workshop.client.post("/v1/me/mfa/recovery-codes", headers=headers)
    next_sign_in = login_code_step(workshop, OWNER)

    assert removed.status_code == 204
    assert security["totp_status"] is None
    assert security["recovery_codes_left"] == 0
    assert security["auth_level"] == "one_factor"
    assert removed_again.status_code == 404
    assert no_codes.status_code == 409
    assert "access_token" in next_sign_in
    assert mfa_changes(workshop, session["user"]["id"]) == [
        "totp_factor",
        "totp_factor",
    ]


def test_an_admin_sees_that_an_authenticator_is_required(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)

    security = workshop.client.get(SECURITY_URL, headers=bearer(token)).json()

    assert security["is_mfa_required"] is True
    assert security["totp_status"] == "active"
    assert security["recovery_codes_left"] == 10
    assert security["auth_level"] == "two_factor"
