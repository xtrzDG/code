"""
The platform health alerts (LOG-04, LOG-05): refused webhooks, storage
errors, slow API requests, failed or missing backups, a business's SMS
volume and login codes that go unused, each from the figures the
processes record.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.monitoring import (
    MaintenanceRunKind,
    MaintenanceRunOutcome,
    PlatformAlertCode,
    PlatformSignal,
)
from app.schemas.constants.platform_status import StatusComponent, StatusLevel
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.monitoring.strings import MaintenanceErrorText
from app.schemas.typings.observability.constrained_integers import (
    ServiceLevelEventCount,
)
from app.schemas.typings.users.strings import OtpCodeHash
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.use_cases.platform_status.component_levels import alert_levels
from tests.platform_ops.ops_documents import HOUR, MINUTE, at
from tests.platform_ops.ops_world import OpsWorld
from tests.platform_status.status_world import alert

HEALTH_CODES: tuple[PlatformAlertCode, ...] = (
    PlatformAlertCode.WEBHOOK_SIGNATURE_FAILURES,
    PlatformAlertCode.STORAGE_ERRORS,
    PlatformAlertCode.API_LATENCY,
    PlatformAlertCode.BACKUP_FAILED,
    PlatformAlertCode.TENANT_SMS_VOLUME,
    PlatformAlertCode.OTP_CONVERSION,
)


def observe(world: OpsWorld, code: PlatformAlertCode) -> AlertObservation:
    [observation] = world.checks().run(
        {code: PLATFORM_ALERT_RULES[code]}, world.clock.wall_clock.now_unix()
    )
    return observation


def count(world: OpsWorld, signal: PlatformSignal, times: int) -> None:
    for _ in range(times):
        world.signals.count(signal)


def backup(
    outcome: MaintenanceRunOutcome, finished: Microseconds
) -> MaintenanceRunDocument:
    return MaintenanceRunDocument(
        kind=MaintenanceRunKind.BACKUP,
        outcome=outcome,
        started_at=Microseconds(int(finished) - MINUTE),
        finished_at=finished,
        error=(
            MaintenanceErrorText("BackupToolError: pg_dump exited with code 1")
            if outcome is MaintenanceRunOutcome.FAILED
            else None
        ),
        created_at=finished,
        updated_at=finished,
    )


def login_code(
    created: Microseconds, *, is_used: bool, country: str = "IT"
) -> OtpChallengeDocument:
    return OtpChallengeDocument(
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber("+393331234567"),
        country_code=CountryCode(country),
        delivery_channel=OtpDeliveryChannel.SMS,
        locale=LanguageTag("it"),
        code_hash=OtpCodeHash("ab" * 32),
        expires_at=Microseconds(int(created) + 10 * MINUTE),
        is_consumed=is_used,
        created_at=created,
        updated_at=created,
    )


def test_every_health_alert_is_quiet_on_a_quiet_platform() -> None:
    world = OpsWorld()

    for code in HEALTH_CODES:
        observation = observe(world, code)
        assert observation.is_firing is False, code
        assert int(observation.figure) == 0, code


@pytest.mark.parametrize(
    ("code", "signals", "threshold"),
    [
        (
            PlatformAlertCode.WEBHOOK_SIGNATURE_FAILURES,
            (PlatformSignal.WEBHOOK_REFUSED,),
            30,
        ),
        (
            PlatformAlertCode.STORAGE_ERRORS,
            (PlatformSignal.DATABASE_ERROR, PlatformSignal.OBJECT_STORAGE_ERROR),
            5,
        ),
        (PlatformAlertCode.TENANT_SMS_VOLUME, (PlatformSignal.TENANT_SMS_SURGE,), 0),
    ],
)
def test_a_burst_above_the_threshold_fires(
    code: PlatformAlertCode,
    signals: tuple[PlatformSignal, ...],
    threshold: int,
) -> None:
    at_threshold = OpsWorld()
    above = OpsWorld()
    for index in range(threshold):
        at_threshold.signals.count(signals[index % len(signals)])
    for index in range(threshold + 1):
        above.signals.count(signals[index % len(signals)])

    assert observe(at_threshold, code).is_firing is False
    fired = observe(above, code)
    assert fired.is_firing is True
    assert int(fired.figure) == threshold + 1


def test_storage_errors_name_each_store() -> None:
    world = OpsWorld()
    count(world, PlatformSignal.DATABASE_ERROR, 4)
    count(world, PlatformSignal.OBJECT_STORAGE_ERROR, 3)

    observation = observe(world, PlatformAlertCode.STORAGE_ERRORS)

    assert observation.is_firing is True
    assert "4 requests or jobs failed on the database and 3 on the object" in str(
        observation.detail
    )


def api_requests(world: OpsWorld, total: int) -> None:
    world.slot_repo.add(
        ServiceLevelSeries.API_AVAILABILITY,
        at(-10 * MINUTE),
        ServiceLevelEventCount(total),
        ServiceLevelEventCount(total),
    )


@pytest.mark.parametrize(
    ("requests", "slow", "is_firing"),
    [
        (1000, 50, False),  # exactly 5 %
        (1000, 51, True),
        (199, 100, False),  # below the volume floor
        (0, 3, False),
    ],
)
def test_api_latency_is_a_share_of_the_requests(
    requests: int, slow: int, is_firing: bool
) -> None:
    world = OpsWorld()
    api_requests(world, requests)
    count(world, PlatformSignal.SLOW_API_REQUEST, slow)

    observation = observe(world, PlatformAlertCode.API_LATENCY)

    assert observation.is_firing is is_firing


def test_requests_older_than_the_window_do_not_count() -> None:
    world = OpsWorld()
    world.slot_repo.add(
        ServiceLevelSeries.API_AVAILABILITY,
        at(-2 * HOUR),
        ServiceLevelEventCount(10_000),
        ServiceLevelEventCount(10_000),
    )
    api_requests(world, 300)
    count(world, PlatformSignal.SLOW_API_REQUEST, 30)

    observation = observe(world, PlatformAlertCode.API_LATENCY)

    assert observation.is_firing is True
    assert "30 of 300 API requests" in str(observation.detail)


def test_a_failed_backup_fires_until_one_succeeds() -> None:
    world = OpsWorld()
    world.run_repo.record(backup(MaintenanceRunOutcome.FAILED, at(-HOUR)))

    failed = observe(world, PlatformAlertCode.BACKUP_FAILED)
    world.run_repo.record(backup(MaintenanceRunOutcome.SUCCEEDED, at(-MINUTE)))
    recovered = observe(world, PlatformAlertCode.BACKUP_FAILED)

    assert failed.is_firing is True
    assert "pg_dump exited with code 1" in str(failed.detail)
    assert recovered.is_firing is False


@pytest.mark.parametrize(
    ("hours_ago", "is_firing"), [(25, False), (26, False), (27, True)]
)
def test_a_backup_older_than_26_hours_fires(hours_ago: int, is_firing: bool) -> None:
    world = OpsWorld()
    world.run_repo.record(
        backup(MaintenanceRunOutcome.SUCCEEDED, at(-hours_ago * HOUR))
    )

    assert observe(world, PlatformAlertCode.BACKUP_FAILED).is_firing is is_firing


def test_unused_login_codes_fire_and_name_their_countries() -> None:
    world = OpsWorld()
    for minute in range(30):
        world.otp_challenges.save(
            login_code(at(-(20 + minute) * MINUTE), is_used=False, country="LV")
        )
    for minute in range(5):
        world.otp_challenges.save(login_code(at(-(20 + minute) * MINUTE), is_used=True))
    # Still in flight (neither used nor expired) and too old: not counted.
    world.otp_challenges.save(login_code(at(-MINUTE), is_used=False))
    world.otp_challenges.save(login_code(at(-2 * HOUR), is_used=False))

    observation = observe(world, PlatformAlertCode.OTP_CONVERSION)

    assert observation.is_firing is True
    assert int(observation.figure) == round(30 * 100 / 35)
    assert "30 of 35 login codes" in str(observation.detail)
    assert "most to LV 30." in str(observation.detail)


def test_codes_people_use_or_too_few_codes_stay_quiet() -> None:
    used = OpsWorld()
    few = OpsWorld()
    for minute in range(30):
        used.otp_challenges.save(
            login_code(at(-(20 + minute) * MINUTE), is_used=minute % 2 == 0)
        )
    for minute in range(19):
        few.otp_challenges.save(login_code(at(-(20 + minute) * MINUTE), is_used=False))

    assert observe(used, PlatformAlertCode.OTP_CONVERSION).is_firing is False
    assert observe(few, PlatformAlertCode.OTP_CONVERSION).is_firing is False


def test_storage_errors_and_latency_degrade_the_status_page() -> None:
    world = OpsWorld()
    count(world, PlatformSignal.DATABASE_ERROR, 6)
    observation = observe(world, PlatformAlertCode.STORAGE_ERRORS)
    checked: int = int(world.clock.wall_clock.now_unix())

    storage_levels = alert_levels(
        [alert(PlatformAlertCode.STORAGE_ERRORS, int(observation.figure), checked)]
    )
    latency_levels = alert_levels([alert(PlatformAlertCode.API_LATENCY, 9, checked)])

    assert observation.is_firing is True
    for component in (
        StatusComponent.CHAT,
        StatusComponent.VOICE,
        StatusComponent.CABINET,
    ):
        assert storage_levels[component] is StatusLevel.DEGRADED, component
    assert latency_levels[StatusComponent.CHAT] is StatusLevel.DEGRADED
    assert latency_levels[StatusComponent.CABINET] is StatusLevel.DEGRADED
    assert latency_levels[StatusComponent.VOICE] is StatusLevel.OPERATIONAL
