"""
A change of a person's second factor reaches every session of theirs, not
only the one that made it: removing the authenticator or replacing the
recovery codes lowers the other sessions to one factor (the admin pages
refuse them), confirming a new authenticator ends them, and a login code
alone never brings two-factor rights back. Each change is audited with how
many sessions it covered.
"""

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE
from tests.users.mfa.mfa_api import (
    RESEND_WAIT_SECONDS,
    STEP_UP_SECONDS,
    reason_codes,
    set_up_authenticator,
)

CLIENTS_URL: str = "/v1/admin/clients"
SECURITY_URL: str = "/v1/me/security"
OWNER: str = GEORGIAN_OWNER_PHONE


def audit_entries(
    workshop: Workshop, action: AuditAction
) -> list[AuditLogEntryDocument]:
    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    return [entry for entry in entries.list_all() if entry.action is action]


def counts(entries: list[AuditLogEntryDocument]) -> list[int | None]:
    return [
        None if entry.record_count is None else int(entry.record_count)
        for entry in entries
    ]


def two_admin_sessions(workshop: Workshop) -> tuple[str, str]:
    token_a, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    workshop.clock.advance(RESEND_WAIT_SECONDS)
    token_b, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    return token_a, token_b


def test_removing_the_authenticator_lowers_every_admin_session(
    workshop: Workshop,
) -> None:
    """The probe: session B is refused after session A removes the app."""

    token_a, token_b = two_admin_sessions(workshop)
    assert workshop.client.get(CLIENTS_URL, headers=bearer(token_b)).status_code == 200

    removed = workshop.client.delete("/v1/me/mfa/totp", headers=bearer(token_a))
    a_admin = workshop.client.get(CLIENTS_URL, headers=bearer(token_a))
    b_admin = workshop.client.get(CLIENTS_URL, headers=bearer(token_b))
    b_security = workshop.client.get(SECURITY_URL, headers=bearer(token_b)).json()

    assert removed.status_code == 204, removed.text
    assert a_admin.status_code == 403
    assert b_admin.status_code == 403
    assert reason_codes(b_admin) == ["mfa_required"]
    assert b_security["auth_level"] == "one_factor"
    assert b_security["totp_status"] is None
    # The removal counts both sessions it lowered.
    assert counts(audit_entries(workshop, AuditAction.MFA_CHANGED))[-1] == 2


def test_a_login_code_does_not_bring_two_factors_back(workshop: Workshop) -> None:
    token_a, token_b = two_admin_sessions(workshop)
    workshop.client.delete("/v1/me/mfa/totp", headers=bearer(token_a))
    workshop.clock.advance(STEP_UP_SECONDS + 1)

    started = workshop.client.post("/v1/auth/step-up", headers=bearer(token_b))
    confirmed = workshop.client.post(
        "/v1/auth/step-up/verify",
        json={
            "challenge_id": started.json()["login_code"]["challenge_id"],
            "login_code": str(workshop.otp.codes[-1].code),
        },
        headers=bearer(token_b),
    )
    b_admin = workshop.client.get(CLIENTS_URL, headers=bearer(token_b))

    assert started.json()["method"] == "login_code"
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["auth_level"] == "one_factor"
    assert b_admin.status_code == 403


def test_new_recovery_codes_lower_the_other_sessions_only(
    workshop: Workshop,
) -> None:
    token_a, token_b = two_admin_sessions(workshop)

    renewed = workshop.client.post("/v1/me/mfa/recovery-codes", headers=bearer(token_a))
    a_admin = workshop.client.get(CLIENTS_URL, headers=bearer(token_a))
    b_admin = workshop.client.get(CLIENTS_URL, headers=bearer(token_b))

    assert renewed.status_code == 200, renewed.text
    assert a_admin.status_code == 200
    assert b_admin.status_code == 403
    [entry] = [
        entry
        for entry in audit_entries(workshop, AuditAction.MFA_CHANGED)
        if str(entry.entity) == "recovery_codes"
    ]
    assert entry.record_count is not None and int(entry.record_count) == 1


def test_a_new_authenticator_ends_every_other_session(workshop: Workshop) -> None:
    token_a, session = workshop.sign_in_with_phone(OWNER)
    workshop.clock.advance(RESEND_WAIT_SECONDS)
    token_b, _ = workshop.sign_in_with_phone(OWNER)
    workshop.clock.advance(RESEND_WAIT_SECONDS)
    token_c, _ = workshop.sign_in_with_phone(OWNER)

    set_up_authenticator(workshop, token_a, OWNER)
    a_me = workshop.client.get("/v1/me", headers=bearer(token_a))
    b_me = workshop.client.get("/v1/me", headers=bearer(token_b))
    c_me = workshop.client.get("/v1/me", headers=bearer(token_c))

    assert a_me.status_code == 200
    assert (b_me.status_code, c_me.status_code) == (401, 401)
    [revoked] = audit_entries(workshop, AuditAction.SESSION_REVOKED)
    user_id: str = session["user"]["id"]
    assert str(revoked.actor_id) == user_id
    assert str(revoked.entity_id) == f"{user_id}:authenticator_added"
    assert revoked.record_count is not None and int(revoked.record_count) == 2
    assert revoked.business_id is None


def test_nothing_is_audited_when_no_other_session_exists(
    workshop: Workshop,
) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER)

    set_up_authenticator(workshop, token, OWNER)
    renewed = workshop.client.post("/v1/me/mfa/recovery-codes", headers=bearer(token))

    assert renewed.status_code == 200
    assert audit_entries(workshop, AuditAction.SESSION_REVOKED) == []
    assert counts(audit_entries(workshop, AuditAction.MFA_CHANGED)) == [None, 0]
