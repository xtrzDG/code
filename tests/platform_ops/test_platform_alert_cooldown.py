"""
The platform alerts job pages once per episode and cooldown: a dead job is
told at once, every five-minute check of the next hour stays quiet, the
episode is told again after the cooldown and once more when it resolves.
"""

import json

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformAlertStatus
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.platform.constrained_strings import JobName
from tests.platform_ops.ops_documents import MINUTE, NOW, job
from tests.platform_ops.ops_world import ALERT_CHAT, ALERT_EMAIL, OpsWorld, put

TICK: JobTick = JobTick(job_name=JobName("platform_alerts"), scheduled_at=NOW)


def first_lines(world: OpsWorld) -> list[str]:
    """The first line of each queued alert message (one per recipient)."""

    return [
        str(json.loads(str(queued.payload))["text"]).splitlines()[0]
        for queued in world.queue.jobs
    ]


def test_an_alert_fires_once_per_cooldown() -> None:
    world = OpsWorld()
    dead = job(QueuedJobStatus.DEAD)
    put(world.jobs, dead)
    use_case = world.alerts_use_case(cooldown_minutes=60)

    reports = [use_case.run(TICK)]
    for _ in range(11):
        world.clock.advance(5 * MINUTE)
        reports.append(use_case.run(TICK))
    within_cooldown = first_lines(world)
    world.clock.advance(5 * MINUTE)
    again = use_case.run(TICK)

    assert [int(report.processed_count) for report in reports] == [2] + [0] * 11
    assert within_cooldown == ["[SEV2] FIRING: Dead jobs"] * 2
    assert int(again.processed_count) == 2
    assert first_lines(world)[2:] == ["[SEV2] STILL FIRING: Dead jobs"] * 2
    [state] = world.alert_state_repo.get_many([PlatformAlertCode.DEAD_JOBS])
    assert state.status is PlatformAlertStatus.FIRING
    assert int(state.notification_count) == 2


def test_a_resolved_alert_is_told_once_and_can_fire_again() -> None:
    world = OpsWorld()
    dead = job(QueuedJobStatus.DEAD)
    put(world.jobs, dead)
    use_case = world.alerts_use_case()
    use_case.run(TICK)

    world.jobs.delete(str(dead.id))
    world.clock.advance(5 * MINUTE)
    resolved = use_case.run(TICK)
    world.clock.advance(5 * MINUTE)
    quiet = use_case.run(TICK)
    put(world.jobs, job(QueuedJobStatus.DEAD))
    world.clock.advance(5 * MINUTE)
    fired_again = use_case.run(TICK)

    assert int(resolved.processed_count) == 2
    assert int(quiet.processed_count) == 0
    assert int(fired_again.processed_count) == 2
    assert first_lines(world) == [
        "[SEV2] FIRING: Dead jobs",
        "[SEV2] FIRING: Dead jobs",
        "[SEV2] RESOLVED: Dead jobs",
        "[SEV2] RESOLVED: Dead jobs",
        "[SEV2] FIRING: Dead jobs",
        "[SEV2] FIRING: Dead jobs",
    ]
    [state] = world.alert_state_repo.get_many([PlatformAlertCode.DEAD_JOBS])
    assert int(state.notification_count) == 1
    assert state.resolved_at is None


def test_each_recipient_gets_its_own_outbound_job() -> None:
    world = OpsWorld()
    put(world.jobs, job(QueuedJobStatus.DEAD, name="import_website"))

    world.alerts_use_case().run(TICK)

    telegram, email = world.queue.jobs
    assert {telegram.lane, email.lane} == {JobLane.OUTBOUND}
    assert telegram.business_id is None and email.business_id is None
    assert telegram.serial_key != email.serial_key
    assert str(ALERT_CHAT) not in str(telegram.serial_key)
    sent_to_chat = json.loads(str(telegram.payload))
    sent_by_email = json.loads(str(email.payload))
    assert sent_to_chat["channel"] == ManagerContactChannel.TELEGRAM.value
    assert sent_to_chat["address"] == str(ALERT_CHAT)
    assert sent_by_email["address"] == str(ALERT_EMAIL)
    text = str(sent_to_chat["text"])
    assert "Dead jobs: 1 (import_website 1)." in text
    assert "Runbook: docs/operations/runbooks/stuck-worker.md" in text
    assert "System page: https://cabinet.workshop.example/admin/system" in text


def test_without_recipients_the_episode_is_kept_but_nothing_is_queued() -> None:
    world = OpsWorld()
    put(world.jobs, job(QueuedJobStatus.DEAD))

    report = world.alerts_use_case(chat_ids=(), emails=()).run(TICK)

    assert int(report.processed_count) == 0
    assert world.queue.jobs == []
    [state] = world.alert_state_repo.get_many([PlatformAlertCode.DEAD_JOBS])
    assert state.status is PlatformAlertStatus.FIRING


def test_a_quiet_platform_writes_nothing() -> None:
    world = OpsWorld()

    report = world.alerts_use_case().run(TICK)

    assert int(report.processed_count) == 0
    assert world.alert_state_repo.get_many(list(PlatformAlertCode)) == []
