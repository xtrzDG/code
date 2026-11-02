"""
A fresh token after a proof raised a one-factor session to two factors:
the proof is not written on the session but waits as a one-time rotation
ticket for the client that made it. With the ticket (once, while it is
fresh, with the token of its own session) that client gets a new token
carrying the two factors, the proof, the device and the expiries; the old
token stays one factor without a proof, answers 30 seconds more, then
ends, and never takes a proof or a ticket again.
"""

import pytest

from app.schemas.constants.mfa import AuthLevel
from app.schemas.dto.sessions import RotateSessionCommand, SessionProof
from app.schemas.dto.users import LoginSessionView
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ConflictError,
)
from app.schemas.typings.users.constrained_strings import SessionRotationTicket
from app.use_cases.users.sessions.session_proofs import record_proof
from app.utilities.security.session_rotation_tickets import (
    ROTATION_GRACE_SECONDS,
    ROTATION_TICKET_TTL_SECONDS,
    generate_rotation_ticket,
)
from tests.users.access.rotation_steps import (
    as_request,
    may_confirm_sensitive_actions,
    prove,
    raise_level,
    rotate,
    rotation,
    stored,
)
from tests.users.access.session_steps import HOME_IP, IPHONE_SAFARI, MINUTE, check
from tests.users.accounts_phones import GEORGIA_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


def signed_in_long_ago(testbed: AccountsTestbed) -> LoginSessionView:
    """A one-factor session whose sign-in no longer confirms anything."""

    signed_in = testbed.sign_in_with_phone(
        GEORGIA_MOBILE, user_agent=IPHONE_SAFARI, client_ip=HOME_IP
    )
    testbed.clock.advance(int(testbed.settings.step_up_max_age_seconds) + MINUTE)
    return signed_in


def test_only_the_rotated_token_carries_the_raised_level() -> None:
    testbed = build_accounts_testbed()
    signed_in = signed_in_long_ago(testbed)
    before = stored(testbed, signed_in)
    proven_at = testbed.clock.build_wall_clock().now_unix()

    ticket = raise_level(testbed, signed_in)
    # Until the swap the old token is what it was: one factor, an old proof.
    waiting = testbed.authenticate_user.run(check(signed_in))
    assert (waiting.auth_level, waiting.authenticated_at) == (
        AuthLevel.ONE_FACTOR,
        before.authenticated_at,
    )
    assert not may_confirm_sensitive_actions(testbed, signed_in)
    before = stored(testbed, signed_in)
    rotated = rotate(testbed, signed_in, ticket)

    after = stored(testbed, rotated)
    assert rotated.access_token != signed_in.access_token
    assert (rotated.user.id, rotated.auth_level, rotated.is_new_user) == (
        signed_in.user.id,
        AuthLevel.TWO_FACTOR,
        False,
    )
    assert after.id != before.id
    assert (after.auth_level, after.authenticated_at) == (
        AuthLevel.TWO_FACTOR,
        proven_at,
    )
    assert (after.expires_at, after.idle_expires_at, rotated.expires_at) == (
        before.expires_at,
        before.idle_expires_at,
        before.expires_at,
    )
    assert (after.user_agent, after.created_ip, after.created_at) == (
        before.user_agent,
        before.created_ip,
        before.created_at,
    )
    assert after.rotation_ticket_hash is None
    assert may_confirm_sensitive_actions(testbed, rotated)
    winding = testbed.authenticate_user.run(check(signed_in))
    assert (winding.session_id, winding.auth_level, winding.authenticated_at) == (
        before.id,
        AuthLevel.ONE_FACTOR,
        None,
    )
    assert not may_confirm_sensitive_actions(testbed, signed_in)
    testbed.clock.advance(ROTATION_GRACE_SECONDS)
    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(check(signed_in))
    assert testbed.authenticate_user.run(check(rotated)).session_id == after.id


def test_rotating_without_the_ticket_is_refused() -> None:
    testbed = build_accounts_testbed()
    signed_in = signed_in_long_ago(testbed)
    issued = raise_level(testbed, signed_in)

    with pytest.raises(ConflictError):
        rotate(testbed, signed_in, generate_rotation_ticket())

    # The guessed ticket burnt nothing: the real one still swaps the token.
    assert stored(testbed, signed_in).auth_level is AuthLevel.ONE_FACTOR
    assert rotate(testbed, signed_in, issued).auth_level is AuthLevel.TWO_FACTOR


def test_a_session_that_proved_nothing_cannot_rotate() -> None:
    testbed = build_accounts_testbed()
    # Even right after sign-in: no raising proof, no ticket.
    signed_in = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    with pytest.raises(ConflictError):
        rotate(testbed, signed_in, generate_rotation_ticket())

    assert testbed.authenticate_user.run(check(signed_in)).user_id == (
        signed_in.user.id
    )


def test_a_ticket_is_used_once() -> None:
    testbed = build_accounts_testbed()
    signed_in = signed_in_long_ago(testbed)
    ticket = raise_level(testbed, signed_in)
    rotated = rotate(testbed, signed_in, ticket)

    with pytest.raises(ConflictError):
        rotate(testbed, signed_in, ticket)
    with pytest.raises(ConflictError):
        rotate(testbed, rotated, ticket)

    assert len(testbed.user_session_repo.list_by_user(signed_in.user.id)) == 2


def test_a_ticket_belongs_to_its_session_and_expires() -> None:
    testbed = build_accounts_testbed()
    phone = signed_in_long_ago(testbed)
    laptop = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    ticket = raise_level(testbed, phone)

    with pytest.raises(ConflictError):
        rotate(testbed, laptop, ticket)
    testbed.clock.advance(ROTATION_TICKET_TTL_SECONDS)
    with pytest.raises(ConflictError):
        rotate(testbed, phone, ticket)

    assert stored(testbed, phone).auth_level is AuthLevel.ONE_FACTOR
    assert stored(testbed, laptop).auth_level is AuthLevel.ONE_FACTOR


def test_the_old_token_takes_no_proof_once_the_session_rotated() -> None:
    testbed = build_accounts_testbed()
    signed_in = signed_in_long_ago(testbed)
    rotate(testbed, signed_in, raise_level(testbed, signed_in))

    # A copy of the old token: neither a second ticket nor a proof sticks.
    assert prove(testbed, signed_in) == SessionProof()
    assert prove(testbed, signed_in, AuthLevel.ONE_FACTOR) == SessionProof()
    winding = testbed.authenticate_user.run(check(signed_in))
    assert (winding.auth_level, winding.authenticated_at) == (
        AuthLevel.ONE_FACTOR,
        None,
    )


def test_a_lowered_session_loses_its_ticket() -> None:
    testbed = build_accounts_testbed()
    signed_in = signed_in_long_ago(testbed)
    ticket: SessionRotationTicket = raise_level(testbed, signed_in)
    # The person removes their last second factor before the swap.
    testbed.user_session_repo.set_level_for_user(
        signed_in.user.id,
        AuthLevel.ONE_FACTOR,
        testbed.clock.build_wall_clock().now_unix(),
    )

    with pytest.raises(ConflictError):
        rotate(testbed, signed_in, ticket)


def test_a_two_factor_session_records_its_proof_in_place() -> None:
    testbed = build_accounts_testbed()
    signed_in = signed_in_long_ago(testbed)
    rotated = rotate(testbed, signed_in, raise_level(testbed, signed_in))
    testbed.clock.advance(int(testbed.settings.step_up_max_age_seconds) + MINUTE)

    proof = prove(testbed, rotated)

    assert proof == SessionProof(is_recorded=True)
    assert may_confirm_sensitive_actions(testbed, rotated)


def test_rotating_needs_the_person_s_own_session() -> None:
    testbed = build_accounts_testbed()
    mine = signed_in_long_ago(testbed)
    theirs = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    ticket = raise_level(testbed, mine)
    command = RotateSessionCommand(user_id=mine.user.id, rotation_ticket=ticket)

    with pytest.raises(AuthenticationRequiredError):
        rotation(testbed).run(command)
    with pytest.raises(AuthenticationRequiredError):
        as_request(testbed, theirs, lambda: rotation(testbed).run(command))
    assert rotate(testbed, mine, ticket).auth_level is AuthLevel.TWO_FACTOR


def test_a_session_lowered_while_its_proof_runs_is_not_raised_in_place() -> None:
    testbed = build_accounts_testbed()
    signed_in = signed_in_long_ago(testbed)
    rotated = rotate(testbed, signed_in, raise_level(testbed, signed_in))
    testbed.clock.advance(int(testbed.settings.step_up_max_age_seconds) + MINUTE)
    now = testbed.clock.build_wall_clock().now_unix()

    def prove_while_lowered() -> SessionProof:
        # The request read the session as two factors; then the person
        # removed their last factor on another device.
        testbed.user_session_repo.set_level_for_user(
            rotated.user.id, AuthLevel.ONE_FACTOR, now
        )
        return record_proof(
            testbed.session_assurance,
            testbed.user_session_repo,
            rotated.user.id,
            AuthLevel.TWO_FACTOR,
            now,
        )

    proof = as_request(testbed, rotated, prove_while_lowered)

    # Every copy of the lowered token stays one factor; the proof waits as
    # a ticket for this client, as for any other raise.
    assert not proof.is_recorded
    assert proof.rotation_ticket is not None
    assert stored(testbed, rotated).auth_level is AuthLevel.ONE_FACTOR
    assert not may_confirm_sensitive_actions(testbed, rotated)
    assert rotate(testbed, rotated, proof.rotation_ticket).auth_level is (
        AuthLevel.TWO_FACTOR
    )
