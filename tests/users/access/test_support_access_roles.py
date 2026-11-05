"""
Who may do what with support access: a read-only support role never
changes anything, billing never opens a cabinet, only an owner decides
about consent, and every look ends (owner ends it, admin leaves, a new
look replaces the old one).
"""

import pytest

from app.schemas.constants.access import (
    BusinessAccessMode,
    PlatformAdminRole,
    SupportAccessEndReason,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.contacts import ContactListQuery
from app.schemas.dto.support_access import (
    CloseClientCabinetCommand,
    EndSupportAccessCommand,
    SupportAccessQuery,
    UpdateSupportWriteAccessCommand,
)
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId
from tests.foundation.support_access_builders import as_request
from tests.users.access.support_world import SUPPORT_IP, SupportWorld


def allow_changes(world: SupportWorld, user_id: UserId) -> object:
    return world.update_write_access.run(
        UpdateSupportWriteAccessCommand(
            user_id=user_id, business_id=world.business.id, is_allowed=True
        )
    )


def support_reads(world: SupportWorld) -> object:
    return world.as_support(
        lambda: world.testbed.list_contacts.run(
            ContactListQuery(user_id=world.support.id, business_id=world.business.id)
        ),
        BusinessAccessMode.READ,
    )


def support_changes(world: SupportWorld) -> object:
    return world.as_support(
        lambda: world.testbed.authorize_business_access.run(
            BusinessAccessRequest(
                user_id=world.support.id, business_id=world.business.id
            )
        )
    )


def ended_grants(world: SupportWorld) -> list[SupportAccessGrantDocument]:
    grants = world.testbed.grant_repo.list_open_everywhere()
    assert grants == [], "every grant should have ended"
    return grants


def ends(world: SupportWorld) -> list[tuple[UserId | None, str]]:
    return [
        (entry.actor_id, str(entry.ip_address))
        for entry in world.testbed.audit_log_repo.list_by_business(world.business.id)
        if entry.action is AuditAction.SUPPORT_ACCESS_END
    ]


def test_read_only_support_never_changes_even_with_the_owners_consent() -> None:
    world = SupportWorld(PlatformAdminRole.SUPPORT_READONLY)
    access = world.open()
    world.as_owner(lambda: allow_changes(world, world.owner_id))

    support_reads(world)
    with pytest.raises(AccessDeniedError, match="may only look"):
        support_changes(world)
    assert access.can_write is False
    view = world.as_support(
        lambda: world.get_access.run(
            SupportAccessQuery(user_id=world.support.id, business_id=world.business.id)
        ),
        BusinessAccessMode.READ,
    )
    assert (view.write_access.is_allowed, view.viewer_can_write) == (True, False)


def test_billing_admins_cannot_open_a_cabinet() -> None:
    world = SupportWorld(PlatformAdminRole.BILLING)

    with pytest.raises(AccessDeniedError, match="role does not include"):
        world.open()

    assert world.testbed.grant_repo.list_open(world.business.id) == []
    # Without the right to open cabinets the business is not there at all.
    with pytest.raises(NotFoundError):
        support_reads(world)


def test_only_an_owner_decides_about_changes() -> None:
    world = SupportWorld()
    world.open()

    with pytest.raises(AccessDeniedError):
        as_request(
            world.testbed.session_assurance,
            world.staff_id,
            lambda: allow_changes(world, world.staff_id),
        )
    with pytest.raises(AccessDeniedError):
        world.as_support(lambda: allow_changes(world, world.support.id))

    with pytest.raises(AccessDeniedError, match="may only look"):
        support_changes(world)


def test_the_owner_ends_every_look_and_the_consent_at_once() -> None:
    world = SupportWorld()
    world.open()
    world.as_owner(lambda: allow_changes(world, world.owner_id))
    support_changes(world)

    world.as_owner(
        lambda: world.end_access.run(
            EndSupportAccessCommand(
                user_id=world.owner_id,
                business_id=world.business.id,
                client_ip_address=ClientIpAddress("203.0.113.9"),
            )
        )
    )

    ended_grants(world)
    with pytest.raises(AccessDeniedError, match="reason first"):
        support_reads(world)
    assert ends(world) == [(world.owner_id, "203.0.113.9")]
    banner = world.as_owner(
        lambda: world.get_access.run(
            SupportAccessQuery(user_id=world.owner_id, business_id=world.business.id)
        )
    )
    assert (banner.sessions, banner.write_access.is_allowed) == ([], False)


def test_the_admin_leaves_the_cabinet_before_the_hour_is_over() -> None:
    world = SupportWorld()
    world.open()

    close = CloseClientCabinetCommand(
        user_id=world.support.id,
        business_id=world.business.id,
        client_ip_address=ClientIpAddress(SUPPORT_IP),
    )
    world.as_support(lambda: world.close_cabinet.run(close))
    world.as_support(lambda: world.close_cabinet.run(close))

    ended_grants(world)
    assert ends(world) == [(world.support.id, SUPPORT_IP)]
    with pytest.raises(AccessDeniedError, match="reason first"):
        support_reads(world)


def test_opening_again_replaces_the_earlier_look() -> None:
    world = SupportWorld()
    first = world.open()
    world.testbed.clock.advance(10 * 60)

    second = world.open()

    [live] = world.testbed.grant_repo.list_open(world.business.id)
    assert live.id == second.support_access_grant_id
    replaced = world.testbed.grant_repo.get(
        world.business.id, first.support_access_grant_id
    )
    assert replaced is not None
    assert replaced.end_reason is SupportAccessEndReason.REPLACED
    assert int(second.expires_at) > int(first.expires_at)
    support_reads(world)
