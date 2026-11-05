"""
"Sign out everywhere": every session of the person ends, the one asking
too, so each device must sign in again; audited once with the count.
"""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.sessions import RevokeAllSessionsCommand
from app.schemas.dto.users import LoginSessionView
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.use_cases.users.sessions.revoke_all_sessions_use_case import (
    RevokeAllSessionsUseCase,
)
from tests.users.access.session_steps import HOME_IP, MINUTE, check, in_session
from tests.users.accounts_phones import GEORGIA_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


def sign_out_everywhere(testbed: AccountsTestbed) -> RevokeAllSessionsUseCase:
    return RevokeAllSessionsUseCase(
        user_session_repo=testbed.user_session_repo,
        session_assurance=testbed.session_assurance,
        audit_log_repo=testbed.audit_log_repo,
        wall_clock=testbed.clock.build_wall_clock(),
    )


def test_every_token_of_the_person_stops_working_this_one_too() -> None:
    testbed = build_accounts_testbed()
    sessions: list[LoginSessionView] = []
    for _ in range(3):
        sessions.append(testbed.sign_in_with_phone(GEORGIA_MOBILE))
        testbed.clock.advance(MINUTE)
    someone_else = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    here = sessions[0]

    ended = in_session(
        testbed,
        here,
        lambda: sign_out_everywhere(testbed).run(
            RevokeAllSessionsCommand(
                user_id=here.user.id, client_ip_address=ClientIpAddress(HOME_IP)
            )
        ),
    )

    assert int(ended.revoked_count) == 3
    for session in sessions:
        with pytest.raises(AuthenticationRequiredError):
            testbed.authenticate_user.run(check(session))
    assert testbed.authenticate_user.run(check(someone_else)).user_id == (
        someone_else.user.id
    )
    [entry] = [
        entry
        for entry in testbed.audit_log_collection.list_all()
        if entry.action is AuditAction.SESSION_REVOKED
    ]
    assert entry.actor_id == here.user.id
    assert str(entry.entity_id) == f"{here.user.id}:signed_out_everywhere"
    assert entry.record_count is not None and int(entry.record_count) == 3
    assert (entry.business_id, str(entry.ip_address)) == (None, HOME_IP)


def test_signing_out_everywhere_needs_the_person_s_own_session() -> None:
    testbed = build_accounts_testbed()
    mine = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    theirs = testbed.sign_in_with_phone(ISRAEL_MOBILE)

    with pytest.raises(AuthenticationRequiredError):
        sign_out_everywhere(testbed).run(RevokeAllSessionsCommand(user_id=mine.user.id))
    with pytest.raises(AuthenticationRequiredError):
        in_session(
            testbed,
            theirs,
            lambda: sign_out_everywhere(testbed).run(
                RevokeAllSessionsCommand(user_id=mine.user.id)
            ),
        )

    assert testbed.authenticate_user.run(check(mine)).user_id == mine.user.id
