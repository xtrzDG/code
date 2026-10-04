"""
The admin system page's and the alerts' counts across every business, on
the in-memory and on the Postgres storage: jobs by state and lane, the
oldest due job, dead letters by name, worker pulses, channels in ERROR and
expiring tokens, handoffs, the outbox by state and failed tool calls.
"""

import pytest

from app.repositories.platform_activity_repository import PlatformActivityRepository
from app.repositories.system_health_repository import SystemHealthRepository
from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.jobs import QueuedJobDocument, WorkerHeartbeatDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from tests.platform_ops.ops_documents import (
    DAY,
    HOUR,
    MINUTE,
    NOW,
    at,
    business,
    channel,
    handoff,
    job,
    outbound,
    pulse,
    reply,
)
from tests.platform_ops.ops_world import put
from tests.storage.conftest import CollectionFactory

# Rows of several businesses are seeded and counted platform-wide.
pytestmark = pytest.mark.usefixtures("platform_scope")

LAST_HOUR: ActivityWindow = ActivityWindow(since=at(-HOUR), until=at(1))


def health_repo(
    collections: CollectionFactory,
) -> tuple[SystemHealthRepository, dict[str, object]]:
    stores: dict[str, object] = {
        "jobs": collections(QueuedJobDocument, "queued_jobs"),
        "pulses": collections(WorkerHeartbeatDocument, "worker_heartbeats"),
        "channels": collections(ChannelDocument, "channels"),
        "businesses": collections(BusinessDocument, "businesses"),
    }
    return SystemHealthRepository(*stores.values()), stores  # type: ignore[arg-type]


def test_jobs_are_counted_by_state_lane_and_name(
    collections: CollectionFactory,
) -> None:
    repo, stores = health_repo(collections)
    put(
        stores["jobs"],  # type: ignore[arg-type]
        job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(-3 * MINUTE)),
        job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(-MINUTE)),
        job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(HOUR)),
        job(QueuedJobStatus.RUNNING, JobLane.OUTBOUND),
        job(QueuedJobStatus.DEAD, JobLane.OUTBOUND, name="deliver_outbound"),
        job(QueuedJobStatus.DEAD, JobLane.DEFAULT, name="deliver_outbound"),
        job(QueuedJobStatus.DEAD, JobLane.DEFAULT, name="import_website"),
        job(QueuedJobStatus.DONE, JobLane.INBOUND),
        job(QueuedJobStatus.DISCARDED, JobLane.INBOUND),
    )

    tallies = {
        (tally.status, tally.lane): int(tally.count) for tally in repo.count_open_jobs()
    }
    oldest = repo.find_oldest_due_job(JobLane.INBOUND, NOW)

    assert tallies == {
        (QueuedJobStatus.PENDING, JobLane.INBOUND): 3,
        (QueuedJobStatus.RUNNING, JobLane.OUTBOUND): 1,
        (QueuedJobStatus.DEAD, JobLane.OUTBOUND): 1,
        (QueuedJobStatus.DEAD, JobLane.DEFAULT): 2,
    }
    assert int(repo.count_due_jobs(JobLane.INBOUND, NOW)) == 2
    assert oldest is not None and int(oldest.run_at) == int(at(-3 * MINUTE))
    assert repo.find_oldest_due_job(JobLane.AUTOTESTS, NOW) is None
    assert [
        (str(dead.name), int(dead.count)) for dead in repo.count_dead_jobs_by_name()
    ] == [
        ("deliver_outbound", 2),
        ("import_website", 1),
    ]


def test_pulses_and_channels_that_need_the_team(
    collections: CollectionFactory,
) -> None:
    repo, stores = health_repo(collections)
    salon, cafe = business("Salon Ia"), business("Café Lumière")
    put(stores["businesses"], salon, cafe)  # type: ignore[arg-type]
    broken = channel(salon.id, ChannelStatus.ERROR)
    soon = channel(cafe.id, expires_at=at(3 * DAY))
    put(
        stores["channels"],  # type: ignore[arg-type]
        broken,
        soon,
        channel(cafe.id, expires_at=at(60 * DAY)),
        channel(cafe.id),
    )
    put(
        stores["pulses"],  # type: ignore[arg-type]
        pulse("worker-a", at(-MINUTE)),
        pulse("worker-b", at(-2 * DAY)),
    )

    pulses = repo.list_pulses_since(at(-DAY))
    in_error = repo.list_channels_in_error(DocumentQueryLimit(20))
    expiring = repo.list_credentials_expiring_before(
        at(14 * DAY), DocumentQueryLimit(20)
    )
    named = repo.get_businesses([salon.id, cafe.id])

    assert [str(item.host_name) for item in pulses] == ["worker-a"]
    assert [item.id for item in in_error] == [broken.id]
    assert int(repo.count_channels_in_error()) == 1
    assert [item.id for item in expiring] == [soon.id]
    assert sorted(str(item.name) for item in named) == ["Café Lumière", "Salon Ia"]
    assert repo.get_businesses([]) == []


def test_activity_of_a_window_across_businesses(
    collections: CollectionFactory,
) -> None:
    salon, cafe = business("Salon Ia"), business("Café Lumière")
    handoffs = collections(HandoffDocument, "handoffs")
    outbox = collections(OutboundMessageDocument, "outbound_messages")
    messages = collections(MessageDocument, "messages")
    repo = PlatformActivityRepository(handoffs, outbox, messages)
    put(
        handoffs,
        handoff(salon.id, at(-MINUTE)),
        handoff(cafe.id, at(-2 * MINUTE)),
        handoff(cafe.id, at(-3 * MINUTE), is_sandbox=True),
        handoff(cafe.id, at(-2 * HOUR)),
    )
    put(
        outbox,
        outbound(salon.id, OutboundMessageStatus.DELIVERED, at(-MINUTE)),
        outbound(cafe.id, OutboundMessageStatus.DELIVERED, at(-2 * MINUTE)),
        outbound(cafe.id, OutboundMessageStatus.DEAD, at(-3 * MINUTE)),
        outbound(cafe.id, OutboundMessageStatus.DEAD, at(-2 * HOUR)),
    )
    put(
        messages,
        reply(salon.id, at(-MINUTE), has_failed_tool=True),
        reply(cafe.id, at(-2 * MINUTE), has_failed_tool=True),
        reply(cafe.id, at(-3 * MINUTE), has_failed_tool=False),
        reply(cafe.id, at(-2 * HOUR), has_failed_tool=True),
    )

    outbound_tallies = {
        tally.status: int(tally.count) for tally in repo.count_outbound(LAST_HOUR)
    }

    assert int(repo.count_handoffs(LAST_HOUR)) == 2
    assert outbound_tallies == {
        OutboundMessageStatus.DELIVERED: 2,
        OutboundMessageStatus.DEAD: 1,
    }
    assert int(repo.count_tool_error_messages(LAST_HOUR)) == 2
