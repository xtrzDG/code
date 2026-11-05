"""
The security events of signing in and out reach the platform's audit
chain: wrong login codes (LOGIN_FAILED, the last one OTP_LOCKED) name the
destination by its keyed digest, wrong second-factor codes (LOGIN_FAILED,
then MFA_LOCKED) the person, and signing out is LOGOUT. None names a
business; every entry is linked into the platform chain.
"""

from app.schemas.constants.compliance import AuditAction, AuditSecurityEvent
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.utilities.compliance.audit_chain_hashing import (
    PLATFORM_CHAIN_KEY,
    compute_entry_hash,
)
from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE
from tests.users.mfa.mfa_api import (
    RESEND_WAIT_SECONDS,
    login_code_step,
    second_step,
    set_up_authenticator,
    wrong_code_for,
)

OWNER: str = GEORGIAN_OWNER_PHONE
STRANGER: str = "+995 555 00 22 44"


def security_entries(workshop: Workshop) -> list[AuditLogEntryDocument]:
    """The platform chain's entries with a security event, by position."""

    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    return sorted(
        (entry for entry in entries.list_all() if entry.security_event is not None),
        key=lambda entry: int(entry.chain_position or 0),
    )


def events(workshop: Workshop) -> list[AuditSecurityEvent | None]:
    return [entry.security_event for entry in security_entries(workshop)]


def guess_codes(workshop: Workshop, phone: str, guesses: int) -> list[int]:
    """Start a login code for `phone` and send `guesses` wrong codes."""

    workshop.clock.advance(RESEND_WAIT_SECONDS)
    started = workshop.client.post("/v1/auth/otp/start", json={"phone_number": phone})
    assert started.status_code == 200, started.text
    wrong = wrong_code_for(str(workshop.otp.codes[-1].code))
    return [
        workshop.client.post(
            "/v1/auth/otp/verify",
            json={"challenge_id": started.json()["challenge_id"], "code": wrong},
        ).status_code
        for _ in range(guesses)
    ]


def test_wrong_login_codes_are_failed_checks_and_the_last_locks(
    workshop: Workshop,
) -> None:
    _, session = workshop.sign_in_with_phone(OWNER)
    limit: int = int(workshop.container.config.app_settings().otp_max_failed_attempts)

    owner_answers = guess_codes(workshop, OWNER, limit)
    stranger_answers = guess_codes(workshop, STRANGER, 1)

    entries = security_entries(workshop)
    assert owner_answers == [401] * limit
    assert stranger_answers == [401]
    assert [entry.security_event for entry in entries] == [
        AuditSecurityEvent.LOGIN_FAILED
    ] * (limit - 1) + [AuditSecurityEvent.OTP_LOCKED, AuditSecurityEvent.LOGIN_FAILED]
    owner_entries, stranger_entry = entries[:limit], entries[limit]
    assert {str(entry.actor_id) for entry in owner_entries} == {session["user"]["id"]}
    assert stranger_entry.actor_id is None
    assert len({str(entry.entity_id) for entry in owner_entries}) == 1
    assert owner_entries[0].entity_id != stranger_entry.entity_id
    for entry in entries:
        assert entry.action is AuditAction.LOGIN
        assert str(entry.entity) == "login_destination"
        assert str(entry.entity_id).startswith("dest_")
        assert "555" not in str(entry.entity_id)
        assert entry.business_id is None
        assert entry.chain_key == PLATFORM_CHAIN_KEY
        assert entry.entry_hash == compute_entry_hash(entry)


def test_wrong_second_factor_codes_lock_the_step_and_name_the_person(
    workshop: Workshop,
) -> None:
    token, session = workshop.sign_in_with_phone(OWNER)
    set_up_authenticator(workshop, token, OWNER)
    answer = login_code_step(workshop, OWNER)
    right: str = workshop.authenticators.code_for(OWNER, workshop.clock)

    wrong = [
        second_step(workshop, answer, code=wrong_code_for(right)).status_code
        for _ in range(5)
    ]
    locked = second_step(workshop, answer, code=right)

    entries = security_entries(workshop)
    assert wrong == [422] * 5
    assert locked.status_code == 429
    assert [entry.security_event for entry in entries] == [
        AuditSecurityEvent.LOGIN_FAILED
    ] * 4 + [AuditSecurityEvent.MFA_LOCKED]
    for entry in entries:
        assert entry.action is AuditAction.LOGIN
        assert str(entry.entity) == "user"
        assert str(entry.entity_id) == session["user"]["id"]
        assert str(entry.actor_id) == session["user"]["id"]
        assert entry.business_id is None


def test_signing_out_is_a_logout_of_the_session(workshop: Workshop) -> None:
    token, session = workshop.sign_in_with_phone(OWNER)

    signed_out = workshop.client.post("/v1/auth/logout", headers=bearer(token))
    again = workshop.client.post("/v1/auth/logout", headers=bearer(token))

    (entry,) = security_entries(workshop)
    assert signed_out.status_code == 204
    assert again.status_code == 401
    assert entry.action is AuditAction.SESSION_REVOKED
    assert entry.security_event is AuditSecurityEvent.LOGOUT
    assert str(entry.entity) == "user_session"
    assert str(entry.actor_id) == session["user"]["id"]
    assert entry.ip_address is not None
    assert entry.business_id is None


def test_the_platform_chain_links_every_security_event(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER)
    guess_codes(workshop, STRANGER, 2)
    workshop.client.post("/v1/auth/logout", headers=bearer(token))

    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    chain = sorted(
        (
            entry
            for entry in entries.list_all()
            if entry.chain_key == PLATFORM_CHAIN_KEY
        ),
        key=lambda entry: int(entry.chain_position or 0),
    )

    assert events(workshop) == [
        AuditSecurityEvent.LOGIN_FAILED,
        AuditSecurityEvent.LOGIN_FAILED,
        AuditSecurityEvent.LOGOUT,
    ]
    assert [int(entry.chain_position or 0) for entry in chain] == list(
        range(1, len(chain) + 1)
    )
    for before, after in zip(chain, chain[1:], strict=False):
        assert after.prev_hash == before.entry_hash
