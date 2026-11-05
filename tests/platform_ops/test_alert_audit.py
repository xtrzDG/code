"""
The audit log's anomaly alerts: bulk exports or erasures by one business,
one admin in many clients' accounts, many failed sign-in checks for one
destination and a broken hash chain. Each fires above its threshold, once
per episode, and names the business, admin or destination by its id only.
"""

import json
from collections.abc import Callable

from typed_time_provider import Microseconds

from app.schemas.constants.compliance import (
    AuditAction,
    AuditChainStatus,
    AuditSecurityEvent,
)
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformAlertStatus
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.use_cases.admin.alerts.alert_texts import ALERT_TITLES
from app.use_cases.compliance.audit_chain.audit_chain_verification import (
    AuditChainVerification,
)
from app.utilities.compliance.audit_chain_hashing import PLATFORM_CHAIN_KEY
from tests.platform_ops.ops_documents import MINUTE, NOW
from tests.platform_ops.ops_world import OpsWorld

TICK: JobTick = JobTick(job_name=JobName("platform_alerts"), scheduled_at=NOW)
DESTINATION: AuditEntityReference = AuditEntityReference("dest_" + "ab" * 16)
OTHER_DESTINATION: AuditEntityReference = AuditEntityReference("dest_" + "cd" * 16)
NOTICES_PER_FIRING: int = 2  # The platform bot and the e-mail.


def write(
    world: OpsWorld,
    count: int,
    action: AuditAction,
    *,
    business_of: Callable[[int], BusinessId | None],
    entity: str = "contact",
    entity_id: AuditEntityReference | None = None,
    actor: UserId | None = None,
    security_event: AuditSecurityEvent | None = None,
    minutes_ago: int = 30,
) -> None:
    moment = Microseconds(int(NOW) - minutes_ago * MINUTE)
    for index in range(count):
        world.audit.log.append(
            AuditLogEntryDocument(
                business_id=business_of(index),
                actor_id=actor,
                action=action,
                security_event=security_event,
                entity=AuditEntityName(entity),
                entity_id=entity_id,
                created_at=moment,
                updated_at=moment,
            )
        )


def failed_checks(
    world: OpsWorld, count: int, destination: AuditEntityReference
) -> None:
    write(
        world,
        count,
        AuditAction.LOGIN,
        business_of=lambda _: None,
        entity="login_destination",
        entity_id=destination,
        security_event=AuditSecurityEvent.LOGIN_FAILED,
    )


def observe(world: OpsWorld, code: PlatformAlertCode) -> AlertObservation:
    (observation,) = world.checks().run({code: PLATFORM_ALERT_RULES[code]}, NOW)
    return observation


def fires_once(world: OpsWorld, code: PlatformAlertCode) -> str:
    """Runs the alerts twice, five minutes apart; returns the one detail."""

    use_case = world.alerts_use_case(cooldown_minutes=60)
    first = use_case.run(TICK)
    world.clock.advance(5 * MINUTE)
    again = use_case.run(TICK)

    title: str = ALERT_TITLES[code.value]
    headings = [
        str(json.loads(str(queued.payload))["text"]).splitlines()[0]
        for queued in world.queue.jobs
    ]
    rule = PLATFORM_ALERT_RULES[code]
    assert int(first.processed_count) == NOTICES_PER_FIRING
    assert int(again.processed_count) == 0
    assert (
        headings
        == [f"[{rule.severity.value.upper()}] FIRING: {title}"] * NOTICES_PER_FIRING
    )
    [state] = world.alert_state_repo.get_many([code])
    assert state.status is PlatformAlertStatus.FIRING
    assert int(state.notification_count) == 1
    return str(state.detail)


def test_twenty_exports_an_hour_are_allowed_the_next_one_fires_once() -> None:
    world = OpsWorld()
    busy = BusinessId()
    write(world, 15, AuditAction.EXPORT, business_of=lambda _: busy)
    write(world, 5, AuditAction.DELETE, business_of=lambda _: busy)
    write(world, 9, AuditAction.DELETE, business_of=lambda _: busy, entity="booking")
    write(world, 30, AuditAction.EXPORT, business_of=lambda _: busy, minutes_ago=61)
    write(world, 19, AuditAction.EXPORT, business_of=lambda _: BusinessId())

    at_threshold = observe(world, PlatformAlertCode.BULK_PERSONAL_DATA)
    write(world, 1, AuditAction.EXPORT, business_of=lambda _: busy)
    detail = fires_once(world, PlatformAlertCode.BULK_PERSONAL_DATA)

    assert (at_threshold.is_firing, int(at_threshold.figure)) == (False, 20)
    assert detail == (
        f"Business {busy} exported or erased personal data 21 times in the last hour."
    )


def test_invoice_and_receipt_downloads_are_no_personal_data_exports() -> None:
    world = OpsWorld()
    busy = BusinessId()
    write(
        world,
        30,
        AuditAction.EXPORT,
        business_of=lambda _: busy,
        entity="billing_document",
    )
    write(world, 3, AuditAction.EXPORT, business_of=lambda _: busy, entity="booking")

    observation = observe(world, PlatformAlertCode.BULK_PERSONAL_DATA)

    assert (observation.is_firing, int(observation.figure)) == (False, 3)


def test_an_admin_in_eleven_clients_accounts_fires_once() -> None:
    world = OpsWorld()
    admin = UserId()
    clients = [BusinessId() for _ in range(11)]
    write(
        world,
        10,
        AuditAction.ADMIN_ACCESS,
        business_of=lambda index: clients[index],
        entity="business",
        actor=admin,
    )
    write(  # The same clients again count once each.
        world,
        10,
        AuditAction.ADMIN_CREDIT_GRANTED,
        business_of=lambda index: clients[index],
        entity="business",
        actor=admin,
    )
    write(  # An owner's own work in many businesses is not an admin's.
        world,
        11,
        AuditAction.UPDATE,
        business_of=lambda index: clients[index],
        entity="business",
        actor=UserId(),
    )

    ten = observe(world, PlatformAlertCode.TENANT_HOPPING)
    write(
        world,
        1,
        AuditAction.SUPPORT_ACCESS_START,
        business_of=lambda _: clients[10],
        entity="support_access_grant",
        actor=admin,
    )
    detail = fires_once(world, PlatformAlertCode.TENANT_HOPPING)

    assert (ten.is_firing, int(ten.figure)) == (False, 10)
    assert detail == (
        f"Admin {admin} entered or changed 11 clients' accounts in the last hour."
    )


def test_fifty_one_failed_checks_for_one_destination_fire_once() -> None:
    world = OpsWorld()
    failed_checks(world, 50, DESTINATION)
    failed_checks(world, 50, OTHER_DESTINATION)
    write(  # Successful sign-ins are no failed checks.
        world,
        60,
        AuditAction.LOGIN,
        business_of=lambda _: None,
        entity="login_destination",
        entity_id=DESTINATION,
    )

    fifty = observe(world, PlatformAlertCode.FAILED_SIGN_IN_CHECKS)
    write(
        world,
        1,
        AuditAction.LOGIN,
        business_of=lambda _: None,
        entity="login_destination",
        entity_id=DESTINATION,
        security_event=AuditSecurityEvent.OTP_LOCKED,
    )
    detail = fires_once(world, PlatformAlertCode.FAILED_SIGN_IN_CHECKS)

    assert (fifty.is_firing, int(fifty.figure)) == (False, 50)
    assert detail == (
        "51 failed sign-in checks in the last hour for one destination "
        f"(login_destination {DESTINATION})."
    )


def test_a_broken_chain_fires_once_and_names_where() -> None:
    world = OpsWorld()
    failed_checks(world, 3, DESTINATION)
    verification = AuditChainVerification(world.audit.chains)
    world.audit.chains.save_status(verification.verify(PLATFORM_CHAIN_KEY, None, NOW))
    intact = observe(world, PlatformAlertCode.AUDIT_CHAIN_BROKEN)
    (second,) = [
        stored
        for stored in world.audit.entries.list_all()
        if int(stored.chain_position or 0) == 2
    ]
    tampered = second.model_copy(update={"record_count": AuditRecordCount(7)})
    world.audit.entries.upsert(str(tampered.id), tampered)
    previous = world.audit.chains.status_of(PLATFORM_CHAIN_KEY)
    world.audit.chains.save_status(
        verification.verify(PLATFORM_CHAIN_KEY, previous, NOW)
    )

    detail = fires_once(world, PlatformAlertCode.AUDIT_CHAIN_BROKEN)

    assert (intact.is_firing, int(intact.figure)) == (False, 0)
    assert world.audit.chains.count_by_status()[AuditChainStatus.BROKEN] == 1
    assert detail == "Broken audit chains: 1 (platform at 2 (hash_mismatch))."


def test_a_quiet_log_fires_nothing() -> None:
    world = OpsWorld()

    observations = world.checks().run(
        {
            code: PLATFORM_ALERT_RULES[code]
            for code in (
                PlatformAlertCode.BULK_PERSONAL_DATA,
                PlatformAlertCode.TENANT_HOPPING,
                PlatformAlertCode.FAILED_SIGN_IN_CHECKS,
                PlatformAlertCode.AUDIT_CHAIN_BROKEN,
            )
        },
        NOW,
    )

    assert [observation.is_firing for observation in observations] == [False] * 4
    assert [int(observation.figure) for observation in observations] == [0] * 4
