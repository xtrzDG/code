"""
The alert checks that read the job queue, the outbox and the worker pulses:
each fires only above its rule's threshold and floor.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from tests.platform_ops.ops_documents import (
    HOUR,
    MINUTE,
    NOW,
    SECOND,
    at,
    job,
    outbound,
    pulse,
)
from tests.platform_ops.ops_world import OpsWorld, put

SHOP: BusinessId = BusinessId()


def observe(world: OpsWorld, code: PlatformAlertCode) -> AlertObservation:
    [observation] = world.checks().run({code: PLATFORM_ALERT_RULES[code]}, NOW)
    return observation


def test_dead_jobs_fire_from_the_first_one() -> None:
    world = OpsWorld()
    quiet = observe(world, PlatformAlertCode.DEAD_JOBS)
    put(world.jobs, job(QueuedJobStatus.DEAD), job(QueuedJobStatus.DONE))

    firing = observe(world, PlatformAlertCode.DEAD_JOBS)

    assert not quiet.is_firing and str(quiet.detail) == "No dead jobs."
    assert firing.is_firing and int(firing.figure) == 1


def test_the_inbound_backlog_fires_after_two_minutes_of_waiting() -> None:
    world = OpsWorld()
    put(
        world.jobs,
        job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(-90 * SECOND)),
        # Scheduled for later, and in another lane: neither waits.
        job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(10 * MINUTE)),
        job(QueuedJobStatus.PENDING, JobLane.DEFAULT, at(-HOUR)),
    )
    within = observe(world, PlatformAlertCode.INBOUND_BACKLOG)
    put(world.jobs, job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(-121 * SECOND)))

    late = observe(world, PlatformAlertCode.INBOUND_BACKLOG)

    assert not within.is_firing and int(within.figure) == 90
    assert late.is_firing and int(late.figure) == 121
    assert "The oldest of 2 waiting customer messages" in str(late.detail)


def failed_outbox(world: OpsWorld, dead: int, delivered: int) -> None:
    for index in range(dead):
        put(world.outbox, outbound(SHOP, OutboundMessageStatus.DEAD, at(-index - 1)))
    for index in range(delivered):
        put(
            world.outbox,
            outbound(SHOP, OutboundMessageStatus.DELIVERED, at(-index - 1)),
        )


def test_outbound_failures_fire_above_ten_percent_of_twenty() -> None:
    exactly_ten, above, too_few = OpsWorld(), OpsWorld(), OpsWorld()
    failed_outbox(exactly_ten, dead=2, delivered=18)
    failed_outbox(above, dead=3, delivered=22)
    failed_outbox(too_few, dead=10, delivered=9)
    # Pending messages and those older than an hour do not count.
    put(above.outbox, outbound(SHOP, OutboundMessageStatus.PENDING, at(-MINUTE)))
    put(above.outbox, outbound(SHOP, OutboundMessageStatus.DEAD, at(-2 * HOUR)))

    assert not observe(exactly_ten, PlatformAlertCode.OUTBOUND_FAILURES).is_firing
    firing = observe(above, PlatformAlertCode.OUTBOUND_FAILURES)
    assert firing.is_firing and int(firing.figure) == 12
    assert str(firing.detail).startswith("3 of 25 messages")
    assert not observe(too_few, PlatformAlertCode.OUTBOUND_FAILURES).is_firing


def test_a_hung_worker_fires_while_the_others_beat() -> None:
    world = OpsWorld()
    put(
        world.pulses,
        pulse("worker-a", at(-10 * SECOND)),
        pulse("worker-b", at(-15 * MINUTE)),
    )

    firing = observe(world, PlatformAlertCode.STALE_WORKER)

    assert firing.is_firing and int(firing.figure) == 1
    assert str(firing.detail) == "worker-b last beat 15 min ago"


def test_replaced_slow_and_lone_workers_do_not_fire() -> None:
    restarted, deployed, slow, lone = OpsWorld(), OpsWorld(), OpsWorld(), OpsWorld()
    # A restart: the new process started after the old one went silent.
    put(
        restarted.pulses,
        pulse("worker-a", at(-40 * MINUTE)),
        pulse("worker-a2", at(-SECOND), started_at=at(-39 * MINUTE)),
    )
    # A deploy: the silent pulse is of the release before.
    put(
        deployed.pulses,
        pulse("old", at(-20 * MINUTE), release=ReleaseVersion("0ld0ld0ld0ld")),
        pulse("new", at(-SECOND)),
    )
    # A slow tick (under ten minutes) is no hung worker.
    put(slow.pulses, pulse("a", at(-SECOND)), pulse("b", at(-7 * MINUTE)))
    # The job runs in a worker: the freshest pulse is alive by definition.
    put(lone.pulses, pulse("only", at(-3 * HOUR)))

    for world in (restarted, deployed, slow, lone):
        observation = observe(world, PlatformAlertCode.STALE_WORKER)
        assert not observation.is_firing, observation.detail


def test_a_failing_check_does_not_stop_the_others() -> None:
    world = OpsWorld()
    put(world.jobs, job(QueuedJobStatus.DEAD))
    world.health_repo.list_pulses_since = failing_read  # type: ignore[method-assign]

    observations = world.checks().run(PLATFORM_ALERT_RULES, NOW)

    codes = {observation.code for observation in observations}
    assert PlatformAlertCode.STALE_WORKER not in codes
    assert PlatformAlertCode.DEAD_JOBS in codes
    assert len(codes) == len(PLATFORM_ALERT_RULES) - 1


def failing_read(since: Microseconds) -> list[WorkerHeartbeatDocument]:
    raise ExternalServiceError(f"The database is gone (since {int(since)}).")
