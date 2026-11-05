"""
The status page trusts the alert levels only while the alert checks run:
past 15 minutes without a run (or before the first) the chat channels
count as degraded, `monitoring_delayed` says so, and `checked_at` names
the last check; the history records those hours the same way.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    StatusComponent,
    StatusLevel,
)
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.platform_status import PlatformStatusQuery, PlatformStatusView
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.platform_status.get_platform_status_use_case import (
    GetPlatformStatusUseCase,
)
from app.use_cases.platform_status.monitoring_freshness import is_monitoring_delayed
from app.use_cases.platform_status.record_platform_status_use_case import (
    RecordPlatformStatusUseCase,
)
from tests.platform_status.status_world import MINUTE, StatusWorld

TICK = JobTick(job_name=JobName("record_platform_status"), scheduled_at=Microseconds(0))
CHAT_CHANNELS = (StatusComponent.CHAT, StatusComponent.META, StatusComponent.TELEGRAM)


def status(world: StatusWorld) -> PlatformStatusView:
    return GetPlatformStatusUseCase(
        world.alert_repo,
        world.announcement_repo,
        world.day_repo,
        world.monitor_repo,
        world.clock.wall_clock,
    ).run(PlatformStatusQuery())


def levels(view: PlatformStatusView) -> dict[StatusComponent, StatusLevel]:
    return {item.component: item.level for item in view.components}


def test_checks_up_to_fifteen_minutes_old_keep_the_platform_operational() -> None:
    world = StatusWorld()
    checked = world.now
    world.clock.advance(15 * MINUTE)

    view = status(world)

    assert view.level is StatusLevel.OPERATIONAL
    assert not view.monitoring_delayed
    assert view.checked_at == checked


def test_checks_older_than_fifteen_minutes_degrade_the_chat_channels() -> None:
    world = StatusWorld()
    checked = world.now
    world.clock.advance(15 * MINUTE + 1)

    view = status(world)

    assert view.monitoring_delayed
    assert view.checked_at == checked
    assert view.level is StatusLevel.DEGRADED
    assert {component: levels(view)[component] for component in CHAT_CHANNELS} == {
        component: StatusLevel.DEGRADED for component in CHAT_CHANNELS
    }
    assert levels(view)[StatusComponent.VOICE] is StatusLevel.OPERATIONAL
    assert levels(view)[StatusComponent.CABINET] is StatusLevel.OPERATIONAL


def test_a_new_platform_before_its_first_check_is_not_late_yet() -> None:
    world = StatusWorld()
    world.monitors.delete(world.monitors.list_all()[0].monitor.value)

    view = status(world)

    assert not view.monitoring_delayed
    assert view.checked_at is None
    assert view.level is StatusLevel.OPERATIONAL


def test_a_worse_level_than_degraded_stays_while_monitoring_is_delayed() -> None:
    world = StatusWorld()
    world.fire(PlatformAlertCode.WORKER_DOWN, 600)
    world.announce(AnnouncementLevel.OUTAGE, [StatusComponent.TELEGRAM])
    world.clock.advance(20 * MINUTE)

    view = status(world)

    assert view.monitoring_delayed
    assert levels(view)[StatusComponent.CHAT] is StatusLevel.OUTAGE
    assert levels(view)[StatusComponent.TELEGRAM] is StatusLevel.OUTAGE


def test_the_history_records_delayed_hours_as_degraded() -> None:
    world = StatusWorld()
    world.clock.advance(30 * MINUTE)

    RecordPlatformStatusUseCase(
        world.alert_repo,
        world.announcement_repo,
        world.day_repo,
        world.monitor_repo,
        world.clock.wall_clock,
    ).run(TICK)

    chat = next(
        item
        for item in status(world).components
        if item.component is StatusComponent.CHAT
    )
    assert chat.history[-1].level is StatusLevel.DEGRADED


def test_the_freshness_rule_counts_from_the_last_check() -> None:
    now = Microseconds(100 * MINUTE)

    assert not is_monitoring_delayed(None, now)
    assert not is_monitoring_delayed(Microseconds(85 * MINUTE), now)
    assert is_monitoring_delayed(Microseconds(85 * MINUTE - 1), now)
