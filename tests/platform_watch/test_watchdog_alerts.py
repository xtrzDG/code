"""
The watchdog tells the team straight away (platform bot and SMTP, no job
queue) once per episode and cooldown, and shares the episodes with the
workers' `platform_alerts` job: whichever looks first tells the news, the
other stays quiet.
"""

import json
import logging
from collections.abc import Generator
from contextlib import contextmanager

import pytest

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.registries.locks.platform_alert_lock_registry import (
    PlatformAlertLockRegistry,
)
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformAlertStatus
from app.schemas.constants.observability import PipelineState
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.pipeline_health import PipelineWatchReport, PipelineWatchTick
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.admin.alerts.watch_pipeline_use_case import WatchPipelineUseCase
from tests.platform_ops.ops_documents import MINUTE, NOW
from tests.platform_watch.watch_world import CHAT, RecordingStaffSender, WatchWorld

TICK: PipelineWatchTick = PipelineWatchTick()
JOB_TICK: JobTick = JobTick(job_name=JobName("platform_alerts"), scheduled_at=NOW)
DOWN: str = "[SEV1] FIRING: No worker answers"


def queued_headlines(world: WatchWorld) -> list[str]:
    return [
        str(json.loads(str(queued.payload))["text"]).splitlines()[0]
        for queued in world.queue.jobs
    ]


def look_every_minute(
    watchdog: WatchPipelineUseCase, world: WatchWorld, minutes: int
) -> list[PipelineWatchReport]:
    reports: list[PipelineWatchReport] = []
    for _ in range(minutes):
        world.clock.advance(MINUTE)
        reports.append(watchdog.run(TICK))
    return reports


def test_a_dead_worker_is_told_once_per_cooldown() -> None:
    world = WatchWorld(cooldown_minutes=60)
    world.worker_beats()
    watchdog = world.watchdog()

    reports = look_every_minute(watchdog, world, 66)

    # Minute 5: the pulse is exactly five minutes old; minute 6: too old.
    assert [report.pipeline for report in reports[:6]] == [
        PipelineState.FLOWING
    ] * 5 + [PipelineState.STALLED]
    assert [int(report.sent_count) for report in reports] == [0] * 5 + [2] + [
        0
    ] * 59 + [2]
    assert (
        world.sender.headlines()
        == [DOWN, DOWN] + ["[SEV1] STILL FIRING: No worker answers"] * 2
    )
    assert world.sender.sent[0][0] == "telegram" and world.sender.sent[1][0] == "email"
    [state] = world.alert_state_repo.get_many([PlatformAlertCode.WORKER_DOWN])
    assert state.status is PlatformAlertStatus.FIRING
    assert int(state.notification_count) == 2
    assert world.queue.jobs == []


def test_a_returning_worker_resolves_the_episode_once() -> None:
    world = WatchWorld()
    watchdog = world.watchdog()
    watchdog.run(TICK)  # No pulse at all: the workers never came up.

    world.clock.advance(MINUTE)
    world.worker_beats()
    # The worker's own alerts job looks first, then the watchdog.
    world.alerts_use_case().run(JOB_TICK)
    after = watchdog.run(TICK)

    assert world.sender.headlines() == [DOWN, DOWN]
    assert queued_headlines(world) == ["[SEV1] RESOLVED: No worker answers"] * 2
    assert after.pipeline is PipelineState.FLOWING and int(after.sent_count) == 0
    [state] = world.alert_state_repo.get_many([PlatformAlertCode.WORKER_DOWN])
    assert state.status is PlatformAlertStatus.RESOLVED


def test_the_watchdog_tells_the_recovery_when_it_looks_first() -> None:
    world = WatchWorld()
    watchdog = world.watchdog()
    watchdog.run(TICK)

    world.clock.advance(MINUTE)
    world.worker_beats()
    recovered = watchdog.run(TICK)
    world.alerts_use_case().run(JOB_TICK)

    assert int(recovered.sent_count) == 2
    assert world.sender.headlines()[2:] == ["[SEV1] RESOLVED: No worker answers"] * 2
    assert queued_headlines(world) == []


def test_a_backlog_seen_by_both_is_told_once() -> None:
    world = WatchWorld()
    world.worker_beats("srv-batch-worker-1")
    world.customer_waits_since(200)

    watched = world.watchdog().run(TICK)
    world.alerts_use_case().run(JOB_TICK)

    assert watched.pipeline is PipelineState.STALLED
    assert world.sender.headlines() == ["[SEV2] FIRING: Customer messages wait"] * 2
    assert not any("Customer messages wait" in line for line in queued_headlines(world))


def test_one_unreachable_channel_does_not_stop_the_other(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = WatchWorld()
    world.sender = RecordingStaffSender(refused_channels=["telegram"])

    with caplog.at_level(logging.ERROR):
        report = world.watchdog().run(TICK)

    assert int(report.sent_count) == 1
    assert [channel for channel, _ in world.sender.sent] == ["email"]
    assert "telegram: DeliveryNotConfiguredError" in caplog.text
    assert str(CHAT) not in caplog.text


def test_without_recipients_the_episode_is_still_stored() -> None:
    world = WatchWorld()
    world.settings = world.settings.model_copy(
        update={"telegram_chat_ids": [], "emails": []}
    )

    report = world.watchdog().run(TICK)

    assert report.is_leader and int(report.sent_count) == 0
    [state] = world.alert_state_repo.get_many([PlatformAlertCode.WORKER_DOWN])
    assert state.status is PlatformAlertStatus.FIRING


class LockedOut(PlatformAlertLockRegistry):
    """An alert-state lock that cannot be taken (the database is gone)."""

    @contextmanager
    def lock_states(self) -> Generator[None]:
        raise ExternalServiceError("Lock platform-alert-states not taken in 10 s.")
        yield


def test_a_look_without_the_lock_skips_its_turn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = WatchWorld()

    with caplog.at_level(logging.WARNING):
        report = world.watchdog(locks=LockedOut(InMemoryAdvisoryLockAdapter())).run(
            TICK
        )

    assert report == PipelineWatchReport()
    assert world.sender.sent == []
    assert "The pipeline watchdog skipped a look" in caplog.text
