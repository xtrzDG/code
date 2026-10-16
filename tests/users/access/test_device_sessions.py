"""
Device sessions: what each one records, the idle expiry that slides with
use (written at most every five minutes), the absolute end, and the purge.
"""

import pytest

from app.schemas.constants.users import SessionDeviceKind
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.sessions import SessionsQuery
from app.schemas.dto.users import LoginSessionView
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.utilities.security.access_tokens import hash_access_token
from tests.users.access.session_steps import (
    ANDROID_CHROME,
    CAFE_IP,
    DAY,
    HOME_IP,
    IPHONE_SAFARI,
    MAC_CHROME,
    MINUTE,
    check,
    in_session,
)
from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


def stored(testbed: AccountsTestbed, session: LoginSessionView) -> UserSessionDocument:
    found = testbed.user_session_repo.find_by_token_hash(
        hash_access_token(session.access_token)
    )
    assert found is not None
    return found


def test_a_session_records_its_device_and_shows_in_the_list() -> None:
    testbed = build_accounts_testbed()
    laptop = testbed.sign_in_with_phone(
        GEORGIA_MOBILE, user_agent=MAC_CHROME, client_ip=HOME_IP
    )
    testbed.clock.advance(MINUTE)
    phone = testbed.sign_in_with_phone(
        GEORGIA_MOBILE, user_agent=IPHONE_SAFARI, client_ip=CAFE_IP
    )

    listed = in_session(
        testbed,
        laptop,
        lambda: testbed.list_my_sessions.run(SessionsQuery(user_id=laptop.user.id)),
    ).items

    # The request's own session first, then the most recently used.
    assert [item.id for item in listed] == [
        stored(testbed, laptop).id,
        stored(testbed, phone).id,
    ]
    assert [item.is_current for item in listed] == [True, False]
    first, second = listed
    assert (first.device.browser, first.device.operating_system) == ("Chrome", "macOS")
    assert first.device.kind is SessionDeviceKind.DESKTOP
    assert str(first.created_ip) == HOME_IP
    assert (second.device.browser, second.device.kind) == (
        "Safari",
        SessionDeviceKind.PHONE,
    )
    assert str(second.last_seen_ip) == CAFE_IP
    assert second.idle_expires_at is not None


def test_last_use_is_written_at_most_every_five_minutes() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(
        GEORGIA_MOBILE, user_agent=MAC_CHROME, client_ip=HOME_IP
    )
    signed_in = stored(testbed, session)

    testbed.clock.advance(4 * MINUTE)
    testbed.authenticate_user.run(check(session, CAFE_IP, ANDROID_CHROME))
    unchanged = stored(testbed, session)
    testbed.clock.advance(2 * MINUTE)
    testbed.authenticate_user.run(check(session, CAFE_IP, ANDROID_CHROME))
    moved = stored(testbed, session)

    assert unchanged.last_seen_at == signed_in.last_seen_at
    assert str(unchanged.last_seen_ip) == HOME_IP
    assert moved.last_seen_at == testbed.clock.now_microseconds()
    assert str(moved.last_seen_ip) == CAFE_IP
    assert str(moved.user_agent) == ANDROID_CHROME
    assert signed_in.idle_expires_at is not None
    assert moved.idle_expires_at is not None
    assert int(moved.idle_expires_at) - int(signed_in.idle_expires_at) == (
        6 * MINUTE * 1_000_000
    )


def test_a_server_side_client_never_replaces_the_browser() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE, user_agent=MAC_CHROME)

    testbed.clock.advance(10 * MINUTE)
    testbed.authenticate_user.run(check(session, HOME_IP, "node"))

    assert str(stored(testbed, session).user_agent) == MAC_CHROME


def test_an_unused_session_ends_after_a_week() -> None:
    testbed = build_accounts_testbed()
    idle = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    testbed.clock.advance(MINUTE)
    used = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    testbed.clock.advance(6 * DAY)
    testbed.authenticate_user.run(check(used))
    testbed.clock.advance(DAY)

    assert testbed.authenticate_user.run(check(used)).user_id == used.user.id
    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(check(idle))
    assert (
        testbed.user_session_repo.find_by_token_hash(
            hash_access_token(idle.access_token)
        )
        is None
    )


def test_idle_timeout_comes_from_settings() -> None:
    testbed = build_accounts_testbed({"SESSION_IDLE_TIMEOUT_SECONDS": "3600"})
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    testbed.clock.advance(3600)

    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(check(session))


def test_the_daily_purge_removes_sessions_unused_too_long() -> None:
    testbed = build_accounts_testbed()
    idle = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    testbed.clock.advance(7 * DAY)
    fresh = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    purged = testbed.user_session_repo.delete_expired(testbed.clock.now_microseconds())

    assert int(purged) == 1
    assert testbed.user_session_repo.list_by_user(idle.user.id) == [
        stored(testbed, fresh)
    ]
