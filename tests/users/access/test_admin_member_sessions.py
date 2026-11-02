"""
A platform admin sees a client team's sign-ins (counts, last use, masked
logins) and a SUPER admin ends every session of one member: their tokens
stop working, a fresh confirmation is needed, and both the platform's
chain and the client's own log say which admin did it.
"""

import pytest

from app.contracts.session_assurance import StepUpGuardContract
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.dto.admin_sessions import (
    ClientMemberSessionList,
    ClientMembersQuery,
    EndMemberSessionsCommand,
)
from app.schemas.dto.sessions import RevokedSessionsView
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    AuthenticationRequiredError,
    NotFoundError,
)
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.admin.sessions.end_member_sessions_use_case import (
    EndMemberSessionsUseCase,
)
from app.use_cases.admin.sessions.list_client_member_sessions_use_case import (
    ListClientMemberSessionsUseCase,
)
from tests.foundation.access_support import AllowStepUp
from tests.users.access.session_steps import MINUTE, check
from tests.users.access.support_world import SUPPORT_IP, SupportWorld
from tests.users.accounts_phones import GERMANY_MOBILE, ISRAEL_MOBILE


class NotConfirmed(StepUpGuardContract):
    def require_recent_authentication(self) -> None:
        raise StepUpRequiredError("Confirm it is you.")


def admin_check(world: SupportWorld) -> AuthorizePlatformAdminUseCase:
    testbed = world.testbed
    return AuthorizePlatformAdminUseCase(
        testbed.user_repo, testbed.session_assurance, testbed.platform_admins
    )


def members(world: SupportWorld) -> ClientMemberSessionList:
    testbed = world.testbed
    use_case = ListClientMemberSessionsUseCase(
        admin_check(world),
        testbed.business_repo,
        testbed.user_repo,
        testbed.user_session_repo,
        testbed.clock.build_wall_clock(),
    )
    return world.as_support(
        lambda: use_case.run(
            ClientMembersQuery(user_id=world.support.id, business_id=world.business.id)
        )
    )


def end_sessions_of(
    world: SupportWorld,
    member_id: UserId,
    step_up: StepUpGuardContract | None = None,
) -> RevokedSessionsView:
    testbed = world.testbed
    use_case = EndMemberSessionsUseCase(
        admin_check(world),
        testbed.business_repo,
        testbed.user_session_repo,
        testbed.session_assurance,
        testbed.audit_log_repo,
        step_up or AllowStepUp(),
        testbed.clock.build_wall_clock(),
    )
    return world.as_support(
        lambda: use_case.run(
            EndMemberSessionsCommand(
                user_id=world.support.id,
                business_id=world.business.id,
                member_user_id=member_id,
                client_ip_address=ClientIpAddress(SUPPORT_IP),
            )
        )
    )


def test_the_team_list_counts_live_sessions_without_contacts() -> None:
    world = SupportWorld(PlatformAdminRole.SUPPORT_READONLY)
    world.testbed.clock.advance(MINUTE)
    world.testbed.sign_in_with_phone(GERMANY_MOBILE)

    listed = members(world)

    by_role = {item.role: item for item in listed.items}
    assert set(by_role) == {BusinessMemberRole.OWNER, BusinessMemberRole.STAFF}
    staff = by_role[BusinessMemberRole.STAFF]
    assert staff.user_id == world.staff_id
    assert int(staff.live_session_count) == 2
    assert staff.last_seen_at is not None
    assert staff.masked_login is not None
    assert str(staff.masked_login).startswith("+") and "*" in str(staff.masked_login)
    assert GERMANY_MOBILE.replace(" ", "") not in str(staff.masked_login)


def test_a_super_admin_ends_every_session_of_a_member_audited_twice() -> None:
    world = SupportWorld()
    world.testbed.clock.advance(MINUTE)
    second = world.testbed.sign_in_with_phone(GERMANY_MOBILE)

    ended = end_sessions_of(world, world.staff_id)

    assert int(ended.revoked_count) == 2
    with pytest.raises(AuthenticationRequiredError):
        world.testbed.authenticate_user.run(check(second))
    entries = [
        entry
        for entry in world.testbed.audit_log_collection.list_all()
        if entry.action is AuditAction.SESSION_REVOKED
    ]
    assert {entry.business_id for entry in entries} == {None, world.business.id}
    for entry in entries:
        assert entry.actor_id == world.support.id
        assert str(entry.entity_id) == f"{world.staff_id}:ended_by_platform_admin"
        assert entry.record_count is not None and int(entry.record_count) == 2
        assert str(entry.ip_address) == SUPPORT_IP
    [staff] = [item for item in members(world).items if item.user_id == world.staff_id]
    assert int(staff.live_session_count) == 0


def test_ending_sessions_needs_a_fresh_confirmation() -> None:
    world = SupportWorld()

    with pytest.raises(StepUpRequiredError):
        end_sessions_of(world, world.staff_id, NotConfirmed())

    [staff] = [item for item in members(world).items if item.user_id == world.staff_id]
    assert int(staff.live_session_count) == 1


@pytest.mark.parametrize(
    "role", [PlatformAdminRole.SUPPORT_READONLY, PlatformAdminRole.BILLING]
)
def test_only_a_super_admin_ends_sessions(role: PlatformAdminRole) -> None:
    world = SupportWorld(role)

    with pytest.raises(AccessDeniedError, match="role does not include"):
        end_sessions_of(world, world.staff_id)


def test_someone_outside_the_team_is_not_found() -> None:
    world = SupportWorld()
    world.testbed.clock.advance(MINUTE)
    outsider = world.testbed.sign_in_with_phone(ISRAEL_MOBILE)

    with pytest.raises(NotFoundError):
        end_sessions_of(world, outsider.user.id)
    assert world.testbed.authenticate_user.run(check(outsider)).user_id == (
        outsider.user.id
    )
