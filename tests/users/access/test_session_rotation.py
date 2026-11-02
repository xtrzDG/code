"""
A fresh token after a step-up: the session keeps its level, device and
expiries under a new token; the old token answers the requests already on
their way for 30 seconds, as one factor without a proof, then ends; only a
session that proved itself within the step-up window rotates.
"""

import pytest

from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.sessions import RotateSessionCommand
from app.schemas.dto.users import LoginSessionView
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ConflictError,
)
from app.transformers.users.user_view_transformer import UserViewTransformer
from app.use_cases.users.sessions.rotate_session_use_case import (
    ROTATION_GRACE_SECONDS,
    RotateSessionUseCase,
)
from app.utilities.security.access_tokens import hash_access_token
from tests.users.access.session_steps import (
    HOME_IP,
    IPHONE_SAFARI,
    MINUTE,
    check,
    in_session,
)
from tests.users.accounts_phones import GEORGIA_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


def rotation(testbed: AccountsTestbed) -> RotateSessionUseCase:
    return RotateSessionUseCase(
        user_repo=testbed.user_repo,
        user_session_repo=testbed.user_session_repo,
        session_assurance=testbed.session_assurance,
        user_view_transformer=UserViewTransformer(),
        app_settings=testbed.settings,
        wall_clock=testbed.clock.build_wall_clock(),
    )


def stored(testbed: AccountsTestbed, session: LoginSessionView) -> UserSessionDocument:
    found = testbed.user_session_repo.find_by_token_hash(
        hash_access_token(session.access_token)
    )
    assert found is not None
    return found


def rotate(testbed: AccountsTestbed, session: LoginSessionView) -> LoginSessionView:
    return in_session(
        testbed,
        session,
        lambda: rotation(testbed).run(RotateSessionCommand(user_id=session.user.id)),
    )


def test_a_stepped_up_session_gets_a_new_token_and_the_old_one_ends() -> None:
    testbed = build_accounts_testbed()
    signed_in = testbed.sign_in_with_phone(
        GEORGIA_MOBILE, user_agent=IPHONE_SAFARI, client_ip=HOME_IP
    )
    before = stored(testbed, signed_in)
    testbed.clock.advance(2 * MINUTE)
    stepped_up_at = testbed.clock.build_wall_clock().now_unix()
    testbed.user_session_repo.record_authentication(
        before.id, AuthLevel.TWO_FACTOR, stepped_up_at
    )

    rotated = rotate(testbed, signed_in)

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
        stepped_up_at,
    )
    assert (after.expires_at, after.idle_expires_at) == (
        before.expires_at,
        before.idle_expires_at,
    )
    assert (after.user_agent, after.created_ip, after.created_at) == (
        before.user_agent,
        before.created_ip,
        before.created_at,
    )
    assert rotated.expires_at == before.expires_at
    assert testbed.authenticate_user.run(check(rotated)).session_id == after.id
    # The old token, for the requests already on their way: what it was
    # before the step-up (one factor, nothing it may confirm), then over.
    winding = testbed.authenticate_user.run(check(signed_in))
    assert (winding.session_id, winding.auth_level, winding.authenticated_at) == (
        before.id,
        AuthLevel.ONE_FACTOR,
        None,
    )
    testbed.clock.advance(ROTATION_GRACE_SECONDS)
    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(check(signed_in))
    assert testbed.authenticate_user.run(check(rotated)).session_id == after.id


def test_a_session_without_a_recent_proof_keeps_its_token() -> None:
    testbed = build_accounts_testbed()
    signed_in = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    testbed.clock.advance(int(testbed.settings.step_up_max_age_seconds) + MINUTE)

    with pytest.raises(ConflictError):
        rotate(testbed, signed_in)

    assert testbed.authenticate_user.run(check(signed_in)).user_id == (
        signed_in.user.id
    )


def test_rotating_needs_the_person_s_own_session() -> None:
    testbed = build_accounts_testbed()
    mine = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    theirs = testbed.sign_in_with_phone(ISRAEL_MOBILE)

    with pytest.raises(AuthenticationRequiredError):
        rotation(testbed).run(RotateSessionCommand(user_id=mine.user.id))
    with pytest.raises(AuthenticationRequiredError):
        in_session(
            testbed,
            theirs,
            lambda: rotation(testbed).run(RotateSessionCommand(user_id=mine.user.id)),
        )
    assert testbed.authenticate_user.run(check(mine)).user_id == mine.user.id
