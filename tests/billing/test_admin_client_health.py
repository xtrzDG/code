"""Admin access, a client's health details and audited entry to its cabinet."""

import pytest

from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.constants.client_health import CabinetSection
from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.admin import (
    AdminClientQuery,
    AdminClientsQuery,
    OpenClientCabinetCommand,
)
from app.schemas.dto.billing_cabinet import StartCheckoutCommand, StartCheckoutRequest
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from tests.billing.admin_world import build_admin_world


def test_admin_pages_are_for_platform_admins_only() -> None:
    world = build_admin_world()

    with pytest.raises(AccessDeniedError):
        world.testbed.list_clients.run(AdminClientsQuery(user_id=world.owner.id))

    with pytest.raises(AccessDeniedError):
        world.testbed.get_client_health.run(
            AdminClientQuery(user_id=world.owner.id, business_id=world.georgian.id)
        )

    with pytest.raises(AccessDeniedError):
        world.testbed.open_client_cabinet.run(
            OpenClientCabinetCommand(
                user_id=world.owner.id,
                business_id=world.georgian.id,
            )
        )

    assert world.testbed.audit_log_repo.list_by_business(world.georgian.id) == []


def test_client_health_explains_the_summary() -> None:
    world = build_admin_world()
    world.testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=world.owner.id,
            business_id=world.georgian.id,
            request=StartCheckoutRequest(),
        )
    )

    health = world.testbed.get_client_health.run(
        AdminClientQuery(user_id=world.admin.id, business_id=world.georgian.id)
    )

    assert health.summary.business_id == world.georgian.id
    assert str(health.timezone) == "Asia/Tbilisi"
    assert [
        (str(test.scenario_key), test.outcome, [str(note) for note in test.judge_notes])
        for test in health.failed_autotests
    ] == [
        ("booking__ru", AutotestOutcome.FAILED, ["Price invented"]),
        ("handoff__en", AutotestOutcome.ERRORED, []),
    ]
    assert len(health.invoices) == 2
    [payment] = health.payments
    assert int(payment.amount.amount_minor) == 96000
    assert world.testbed.audit_log_repo.list_by_business(world.georgian.id) == []


def test_client_health_of_an_unknown_business_is_not_found() -> None:
    world = build_admin_world()

    with pytest.raises(NotFoundError):
        world.testbed.get_client_health.run(
            AdminClientQuery(user_id=world.admin.id, business_id=BusinessId())
        )

    with pytest.raises(NotFoundError):
        world.testbed.open_client_cabinet.run(
            OpenClientCabinetCommand(user_id=world.admin.id, business_id=BusinessId())
        )


def test_entering_a_client_cabinet_is_audited() -> None:
    world = build_admin_world()

    access = world.testbed.open_client_cabinet.run(
        OpenClientCabinetCommand(
            user_id=world.admin.id,
            business_id=world.italian.id,
            client_ip_address=ClientIpAddress("203.0.113.7"),
        )
    )

    [entry] = world.testbed.audit_log_repo.list_by_business(world.italian.id)
    assert entry.action is AuditAction.ADMIN_ACCESS
    assert entry.actor_id == world.admin.id
    assert str(entry.ip_address) == "203.0.113.7"
    assert str(entry.entity) == "business_cabinet"
    assert access.audit_log_entry_id == entry.id
    assert access.sections == list(CabinetSection)
    assert str(access.owner_language) == "it"
    assert access.opened_at == world.testbed.clock.now()


def test_admin_access_follows_the_platform_admin_flag() -> None:
    world = build_admin_world()
    query = AdminClientsQuery(user_id=world.admin.id)
    world.testbed.list_clients.run(query)
    demoted = world.admin.model_copy(update={"is_platform_admin": False})
    world.testbed.user_repo.save(demoted)

    with pytest.raises(AccessDeniedError):
        world.testbed.list_clients.run(query)
