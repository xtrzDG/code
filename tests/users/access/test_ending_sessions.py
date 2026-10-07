"""
Ending sessions: one (a lost phone), every other one ("sign out
everywhere else"), the tokens stop working at once, and it is audited.
Platform admins' sessions are shorter: twelve hours unused, a day at most.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.sessions import (
    RevokeOtherSessionsCommand,
    RevokeSessionCommand,
    SessionCheck,
)
from app.schemas.dto.users import LoginSessionView
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    NotFoundError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId
from app.schemas.typings.users.strings import AccessToken
from app.utilities.security.access_tokens import (
    generate_access_token,
    hash_access_token,
)
from tests.foundation.access_support import platform_admin
from tests.users.access.session_steps import (
    HOME_IP,
    HOUR,
    MINUTE,
    check,
    in_session,
)
from tests.users.accounts_phones import GEORGIA_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

ADMIN_SETTINGS: dict[str, str] = {"PLATFORM_ADMIN_EMAILS": "platform-admin@example.com"}


def test_revoke_others_kills_the_other_tokens() -> None:
    testbed = build_accounts_testbed()
    sessions: list[LoginSessionView] = []
    for _ in range(3):
        sessions.append(testbed.sign_in_with_phone(GEORGIA_MOBILE))
        testbed.clock.advance(MINUTE)
    here, *elsewhere = sessions

    ended = in_session(
        testbed,
        here,
        lambda: testbed.revoke_other_sessions.run(
            RevokeOtherSessionsCommand(
                user_id=here.user.id, client_ip_address=ClientIpAddress(HOME_IP)
            )
        ),
    )

    assert int(ended.revoked_count) == 2
    for other in elsewhere:
        with pytest.raises(AuthenticationRequiredError):
            testbed.authenticate_user.run(check(other))
    assert testbed.authenticate_user.run(check(here)).user_id == here.user.id
    [entry] = entries_of(testbed, here.user.id)
    assert entry.action is AuditAction.SESSION_REVOKED
    assert (entry.business_id, str(entry.ip_address)) == (None, HOME_IP)


def test_revoke_others_needs_the_request_session() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    with pytest.raises(AuthenticationRequiredError):
        testbed.revoke_other_sessions.run(
            RevokeOtherSessionsCommand(user_id=session.user.id)
        )


def test_one_session_is_ended_and_only_its_owner_may_end_it() -> None:
    testbed = build_accounts_testbed()
    lost_phone = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    testbed.clock.advance(MINUTE)
    laptop = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    stranger = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    lost_id = stored_id(testbed, lost_phone.access_token)

    with pytest.raises(NotFoundError):
        testbed.revoke_session.run(
            RevokeSessionCommand(user_id=stranger.user.id, session_id=lost_id)
        )
    testbed.revoke_session.run(
        RevokeSessionCommand(user_id=laptop.user.id, session_id=lost_id)
    )

    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(check(lost_phone))
    assert testbed.authenticate_user.run(check(laptop)).user_id == laptop.user.id
    [entry] = entries_of(testbed, laptop.user.id)
    assert (entry.action, str(entry.entity_id)) == (
        AuditAction.SESSION_REVOKED,
        str(lost_id),
    )


def test_an_admin_session_ends_after_twelve_idle_hours_or_a_day() -> None:
    testbed = build_accounts_testbed(ADMIN_SETTINGS)
    admin = platform_admin()
    testbed.user_repo.save(admin)
    now = int(testbed.clock.now_microseconds())
    used = admin_session(testbed, admin.id, now)
    idle = admin_session(testbed, admin.id, now)

    # Used every hour: the absolute end (a day after sign-in) comes anyway.
    for _ in range(11):
        testbed.clock.advance(HOUR)
        testbed.authenticate_user.run(SessionCheck(access_token=used))
    testbed.clock.advance(HOUR)
    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(SessionCheck(access_token=idle))
    for _ in range(11):
        testbed.authenticate_user.run(SessionCheck(access_token=used))
        testbed.clock.advance(HOUR)
    assert testbed.authenticate_user.run(SessionCheck(access_token=used))
    testbed.clock.advance(HOUR)
    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(SessionCheck(access_token=used))


def entries_of(
    testbed: AccountsTestbed, actor_id: UserId
) -> list[AuditLogEntryDocument]:
    """The person's SESSION_REVOKED entries."""

    return [
        entry
        for entry in testbed.audit_log_collection.list_all()
        if entry.actor_id == actor_id and entry.action is AuditAction.SESSION_REVOKED
    ]


def admin_session(testbed: AccountsTestbed, user_id: UserId, now: int) -> AccessToken:
    """A 30-day session from before the person became an admin."""

    token = generate_access_token()
    testbed.user_session_repo.save(
        UserSessionDocument(
            user_id=user_id,
            token_hash=hash_access_token(token),
            expires_at=Microseconds(now + 30 * 24 * HOUR * 1_000_000),
            created_at=Microseconds(now),
            updated_at=Microseconds(now),
        )
    )
    return token


def stored_id(testbed: AccountsTestbed, token: AccessToken) -> UserSessionId:
    found = testbed.user_session_repo.find_by_token_hash(hash_access_token(token))
    assert found is not None
    return found.id
