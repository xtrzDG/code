"""
Platform support looks into a client's cabinet only with a reason, for an
hour, read-only and visibly to the owner; changes need the owner's
expiring consent and a SUPER role; every start and end is audited.
"""

import pytest

from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.contacts import ContactListQuery
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.support_access import (
    SupportAccessQuery,
    UpdateSupportWriteAccessCommand,
)
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.access.constrained_integers import SupportWriteAccessHours
from app.schemas.typings.platform.constrained_strings import JobName
from tests.users.access.support_world import REASON, SUPPORT_IP, SupportWorld

HOUR_MICROSECONDS: int = 60 * 60 * 1_000_000


def support_reads(world: SupportWorld) -> object:
    return world.as_support(
        lambda: world.testbed.list_contacts.run(
            ContactListQuery(user_id=world.support.id, business_id=world.business.id)
        ),
        BusinessAccessMode.READ,
    )


SEEDING: frozenset[AuditAction] = frozenset({AuditAction.VIEW, AuditAction.CREATE})


def audit_actions(world: SupportWorld) -> list[tuple[AuditAction, str]]:
    """The business's audit log in a stable order, without seeding and views."""

    return sorted(
        (entry.action, str(entry.entity))
        for entry in world.testbed.audit_log_repo.list_by_business(world.business.id)
        if entry.action not in SEEDING
    )


def test_opening_a_cabinet_lasts_an_hour_is_read_only_and_told() -> None:
    world = SupportWorld()

    access = world.open()

    assert int(access.expires_at) - int(access.opened_at) == HOUR_MICROSECONDS
    assert access.can_write is False
    [entry] = [
        entry
        for entry in world.testbed.audit_log_repo.list_by_business(world.business.id)
        if entry.action is AuditAction.SUPPORT_ACCESS_START
    ]
    assert (str(entry.ip_address), entry.actor_id) == (SUPPORT_IP, world.support.id)
    [(alert, brief)] = world.staff_alerts.alerts
    assert str(REASON) in str(brief.detail)
    assert alert.recipient_user_ids is None
    banner = world.as_owner(
        lambda: world.get_access.run(
            SupportAccessQuery(user_id=world.owner_id, business_id=world.business.id)
        )
    )
    [session] = banner.sessions
    assert (session.reason, session.expires_at, session.is_yours) == (
        REASON,
        access.expires_at,
        False,
    )
    assert banner.is_support_viewer is False
    assert banner.write_access.is_allowed is False
    seen_by_support = world.as_support(
        lambda: world.get_access.run(
            SupportAccessQuery(user_id=world.support.id, business_id=world.business.id)
        ),
        BusinessAccessMode.READ,
    )
    assert seen_by_support.is_support_viewer is True
    assert seen_by_support.sessions[0].is_yours is True
    assert seen_by_support.viewer_can_write is False


def test_a_read_only_grant_cannot_export_or_erase() -> None:
    world = SupportWorld()
    world.open()

    support_reads(world)
    with pytest.raises(AccessDeniedError, match="may only look"):
        world.as_support(
            lambda: world.testbed.export_contact_data.run(world.contact_command()),
            BusinessAccessMode.READ,
        )
    with pytest.raises(AccessDeniedError, match="may only look"):
        world.as_support(
            lambda: world.testbed.delete_contact_data.run(world.contact_command())
        )

    assert world.testbed.contact_repo.get(
        world.business.id, world.tenants.visitor.contact.id
    )


def test_an_expired_grant_is_refused_and_the_job_closes_it() -> None:
    world = SupportWorld()
    world.open()
    world.testbed.clock.advance(60 * 60)

    with pytest.raises(AccessDeniedError, match="reason first"):
        support_reads(world)
    tick = JobTick(
        job_name=JobName("end_expired_support_access"),
        scheduled_at=world.testbed.clock.now_microseconds(),
    )
    first = world.end_expired.run(tick)
    again = world.end_expired.run(tick)

    assert (int(first.processed_count), int(again.processed_count)) == (1, 0)
    [grant] = world.testbed.grant_repo.list_open_of_admin(
        world.business.id, world.support.id
    ) or [None]
    assert grant is None
    ends = [
        entry
        for entry in world.testbed.audit_log_repo.list_by_business(world.business.id)
        if entry.action is AuditAction.SUPPORT_ACCESS_END
    ]
    assert [entry.actor_id for entry in ends] == [None]


def test_changes_need_the_owners_consent_and_stay_off_owner_actions() -> None:
    world = SupportWorld()
    world.open()
    change = BusinessAccessRequest(
        user_id=world.support.id, business_id=world.business.id
    )
    owner_only = change.model_copy(update={"required_role": BusinessMemberRole.OWNER})

    with pytest.raises(AccessDeniedError, match="may only look"):
        world.as_support(lambda: world.testbed.authorize_business_access.run(change))
    world.as_owner(lambda: allow_changes(world, hours=2))
    allowed = world.as_support(
        lambda: world.testbed.authorize_business_access.run(change)
    )
    done_for_you = world.as_support(
        lambda: world.testbed.authorize_business_access.run(
            owner_only.model_copy(update={"support_may_change": True})
        )
    )

    assert allowed.id == done_for_you.id == world.business.id
    with pytest.raises(AccessDeniedError, match="Only the business owner"):
        world.as_support(
            lambda: world.testbed.authorize_business_access.run(owner_only)
        )
    with pytest.raises(AccessDeniedError, match="Only the business owner"):
        world.as_support(
            lambda: world.testbed.export_contact_data.run(world.contact_command())
        )
    assert audit_actions(world) == sorted(
        [
            (AuditAction.SUPPORT_ACCESS_START, "support_access"),
            (AuditAction.UPDATE, "support_write_access"),
            (AuditAction.ADMIN_ACCESS, "business"),
            (AuditAction.ADMIN_ACCESS, "business"),
        ]
    )
    # The consent ends by itself after the hours the owner chose.
    world.testbed.clock.advance(2 * 60 * 60)
    with pytest.raises(AccessDeniedError):
        world.as_support(lambda: world.testbed.authorize_business_access.run(change))


def allow_changes(world: SupportWorld, hours: int | None = None) -> object:
    return world.update_write_access.run(
        UpdateSupportWriteAccessCommand(
            user_id=world.owner_id,
            business_id=world.business.id,
            is_allowed=True,
            hours=None if hours is None else SupportWriteAccessHours(hours),
        )
    )
