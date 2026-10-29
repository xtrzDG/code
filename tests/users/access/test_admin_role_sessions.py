"""
A platform admin whose role changes, or who is taken off the team, signs in
again: every session of theirs ends at once, audited as SESSION_REVOKED by
the SUPER admin with how many sessions ended. Admins who change their own
role keep the session they made the change from.
"""

from collections.abc import Callable
from contextvars import copy_context

from typed_time_provider import Microseconds

from app.schemas.constants.access import PlatformAdminRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.platform_admins import (
    ChangePlatformAdminRoleCommand,
    PlatformAdminTeamView,
    RemovePlatformAdminCommand,
)
from app.schemas.typings.access.prefixed_id import PlatformAdminId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserSessionId
from app.schemas.typings.users.strings import AccessToken
from app.utilities.security.access_tokens import hash_access_token
from tests.users.access.support_world import SUPPORT_IP
from tests.users.access.test_admin_team import TeamWorld

OPS_EMAIL: str = "ops@platform.example"
DAY: int = 24 * 3600 * 1_000_000


def open_sessions(
    world: TeamWorld, user: UserDocument, count: int
) -> list[UserSessionId]:
    now: int = int(world.testbed.clock.build_wall_clock().now_unix())
    sessions: list[UserSessionId] = []
    for index in range(count):
        session = UserSessionDocument(
            user_id=user.id,
            token_hash=hash_access_token(AccessToken(f"{user.id}-token-{index}")),
            expires_at=Microseconds(now + DAY),
            auth_level=AuthLevel.TWO_FACTOR,
            created_at=Microseconds(now),
            updated_at=Microseconds(now),
        )
        world.testbed.user_session_repo.save(session)
        sessions.append(session.id)
    return sessions


def live_sessions(world: TeamWorld, user: UserDocument) -> set[UserSessionId]:
    return {s.id for s in world.testbed.user_session_repo.list_by_user(user.id)}


def revocations(world: TeamWorld) -> list[AuditLogEntryDocument]:
    return [
        entry
        for entry in world.testbed.audit_log_collection.list_all()
        if entry.action is AuditAction.SESSION_REVOKED
    ]


def with_ops_admin(world: TeamWorld) -> tuple[UserDocument, PlatformAdminId]:
    ops: UserDocument = world.add_admin(OPS_EMAIL, PlatformAdminRole.SUPPORT_READONLY)
    team: PlatformAdminTeamView = world.team()
    [record] = [item for item in team.items if item.user_id == ops.id]
    return ops, record.id


def from_session[T](
    world: TeamWorld, session_id: UserSessionId, work: Callable[[], T]
) -> T:
    def request() -> T:
        world.testbed.session_assurance.bind(
            SessionAssurance(
                user_id=world.support.id,
                session_id=session_id,
                auth_level=AuthLevel.TWO_FACTOR,
            )
        )
        return work()

    return copy_context().run(request)


def test_a_role_change_ends_every_session_of_that_admin() -> None:
    world = TeamWorld()
    ops, record_id = with_ops_admin(world)
    open_sessions(world, ops, 2)
    mine = open_sessions(world, world.support, 1)

    world.as_support(
        lambda: world.change.run(
            ChangePlatformAdminRoleCommand(
                user_id=world.support.id,
                admin_id=record_id,
                role=PlatformAdminRole.BILLING,
                client_ip_address=ClientIpAddress(SUPPORT_IP),
            )
        )
    )

    assert live_sessions(world, ops) == set()
    assert live_sessions(world, world.support) == set(mine)
    [entry] = revocations(world)
    assert entry.actor_id == world.support.id
    assert str(entry.entity_id) == f"{ops.id}:admin_role_changed"
    assert entry.record_count is not None and int(entry.record_count) == 2
    assert str(entry.ip_address) == SUPPORT_IP


def test_the_same_role_again_ends_nothing() -> None:
    world = TeamWorld()
    ops, record_id = with_ops_admin(world)
    sessions = open_sessions(world, ops, 1)

    world.as_support(
        lambda: world.change.run(
            ChangePlatformAdminRoleCommand(
                user_id=world.support.id,
                admin_id=record_id,
                role=PlatformAdminRole.SUPPORT_READONLY,
            )
        )
    )

    assert live_sessions(world, ops) == set(sessions)
    assert revocations(world) == []


def test_taking_an_admin_off_the_team_ends_their_sessions() -> None:
    world = TeamWorld()
    ops, record_id = with_ops_admin(world)
    open_sessions(world, ops, 3)

    world.as_support(
        lambda: world.remove.run(
            RemovePlatformAdminCommand(user_id=world.support.id, admin_id=record_id)
        )
    )

    assert live_sessions(world, ops) == set()
    [entry] = revocations(world)
    assert entry.record_count is not None and int(entry.record_count) == 3


def test_an_admin_who_never_signed_in_has_nothing_to_end() -> None:
    world = TeamWorld()
    team = world.add_by(PlatformAdminRole.BILLING, email="new@platform.example")
    [newcomer] = [item for item in team.items if item.user_id is None]

    world.as_support(
        lambda: world.remove.run(
            RemovePlatformAdminCommand(user_id=world.support.id, admin_id=newcomer.id)
        )
    )

    assert revocations(world) == []


def test_changing_your_own_role_keeps_the_session_you_used() -> None:
    world = TeamWorld()
    _, other_id = with_ops_admin(world)
    world.as_support(
        lambda: world.change.run(
            ChangePlatformAdminRoleCommand(
                user_id=world.support.id,
                admin_id=other_id,
                role=PlatformAdminRole.SUPER,
            )
        )
    )
    here, elsewhere = open_sessions(world, world.support, 2)
    [me] = [item for item in world.team().items if item.is_you]

    from_session(
        world,
        here,
        lambda: world.change.run(
            ChangePlatformAdminRoleCommand(
                user_id=world.support.id,
                admin_id=me.id,
                role=PlatformAdminRole.BILLING,
            )
        ),
    )

    assert live_sessions(world, world.support) == {here}
    assert elsewhere not in live_sessions(world, world.support)
