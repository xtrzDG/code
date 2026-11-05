"""
The sweeper of the inbox (`sweep_stale_inbound_events`): an event whose job
was lost is queued again once it is stale and answered exactly once; an
event that still has a job, or that a worker holds, is left alone; a
customer message the assistant gave up on reaches a person once, an hour
later.
"""

import pytest
from typed_time_provider import Microseconds

from app.orchestrators.channels.inbox.sweep_stale_inbound_events_orchestrator import (
    SweepStaleInboundEventsOrchestrator,
)
from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffSummaryCode,
    HandoffUrgency,
)
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.handoffs import CodedHandoffSummary
from app.schemas.dto.jobs import JobTick
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.channels.inbox.collect_unanswered_inbound_events_use_case import (
    CollectUnansweredInboundEventsUseCase,
)
from app.use_cases.channels.inbox.mark_inbound_event_handed_off_use_case import (
    MarkInboundEventHandedOffUseCase,
)
from app.use_cases.channels.inbox.requeue_stale_inbound_events_use_case import (
    RequeueStaleInboundEventsUseCase,
)
from tests.channels.outbox_reads import inbox
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed

ANSWER: str = "Reply: Do you have a table for 4 tonight?"
# Twice the inbox event's processing lease (180 s), and a second more.
PAST_STALE_SECONDS: int = 361
HOUR_SECONDS: int = 3600


def sweep(testbed: ChannelsTestbed) -> int:
    """One run of the periodic job: how many events it took care of."""

    orchestrator = SweepStaleInboundEventsOrchestrator(
        RequeueStaleInboundEventsUseCase(
            testbed.inbound_event_repo,
            testbed.jobs.job_repo,
            testbed.job_queue,
            testbed.wall_clock,
        ),
        CollectUnansweredInboundEventsUseCase(
            testbed.inbound_event_repo,
            testbed.business_repo,
            testbed.conversation_repo,
            testbed.wall_clock,
        ),
        testbed.handoffs_to_human,
        MarkInboundEventHandedOffUseCase(
            testbed.inbound_event_repo, testbed.wall_clock
        ),
    )
    report = orchestrator.execute(
        JobTick(
            job_name=JobName("sweep_stale_inbound_events"),
            scheduled_at=testbed.wall_clock.now_unix(),
        )
    )
    return int(report.processed_count)


def delivered_texts(testbed: ChannelsTestbed) -> list[str]:
    return [
        str(request.json()["text"])
        for request in testbed.telegram_transport.requests_to("/sendMessage")
    ]


def store_without_its_job(
    testbed: ChannelsTestbed, monkeypatch: pytest.MonkeyPatch
) -> tuple[ChannelDocument, InboundEventDocument]:
    """
    The webhook stores the event, and the process dies before the job is
    queued (without a unit of work: an older release, or in memory).
    """

    _, channel = connect_bot(testbed)

    def lose_the_job(*args: object, **kwargs: object) -> None:
        raise ExternalServiceError("database connection lost")

    with monkeypatch.context() as patch:
        patch.setattr(testbed.job_queue, "enqueue", lose_the_job)
        response = post_update(testbed, channel, build_update())

    # Telegram is told to send it again (and would, after a real crash).
    assert response.status_code >= 500, response.text

    [event] = inbox(testbed)
    return channel, event


def test_an_event_whose_job_was_lost_is_queued_again_and_answered_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = ChannelsTestbed()
    store_without_its_job(testbed, monkeypatch)
    testbed.run_worker()
    assert delivered_texts(testbed) == []

    # Not stale yet: a job may still be on its way.
    testbed.clock.advance(PAST_STALE_SECONDS - 60)
    assert sweep(testbed) == 0

    testbed.clock.advance(60)
    assert sweep(testbed) == 1
    testbed.run_worker()

    assert delivered_texts(testbed) == [ANSWER]
    [answered] = inbox(testbed)
    assert answered.status is InboundEventStatus.ANSWERED
    # Swept again: nothing is stale, nothing is sent twice.
    testbed.clock.advance(PAST_STALE_SECONDS)
    assert sweep(testbed) == 0
    testbed.run_worker()
    assert delivered_texts(testbed) == [ANSWER]


def test_the_webhook_redelivered_after_a_crash_is_answered_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = ChannelsTestbed()
    channel, _ = store_without_its_job(testbed, monkeypatch)

    # Telegram sends the update again: the stored event gets its job.
    assert post_update(testbed, channel, build_update()).status_code == 200
    testbed.run_worker()
    testbed.clock.advance(PAST_STALE_SECONDS)
    assert sweep(testbed) == 0
    testbed.run_worker()

    assert delivered_texts(testbed) == [ANSWER]
    [answered] = inbox(testbed)
    assert answered.status is InboundEventStatus.ANSWERED


def test_an_event_with_a_waiting_job_is_left_alone() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    post_update(testbed, channel, build_update())

    # The worker was down for a while: the job still waits in the queue.
    testbed.clock.advance(PAST_STALE_SECONDS)
    assert sweep(testbed) == 0
    testbed.run_worker()

    assert delivered_texts(testbed) == [ANSWER]


def test_an_event_a_worker_holds_is_left_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testbed = ChannelsTestbed()
    _, event = store_without_its_job(testbed, monkeypatch)
    testbed.clock.advance(PAST_STALE_SECONDS)
    held_until = Microseconds(int(testbed.wall_clock.now_unix()) + 60_000_000)

    def hold(current: InboundEventDocument) -> InboundEventDocument:
        current.status = InboundEventStatus.PROCESSING
        current.lease_until = held_until
        return current

    testbed.inbound_event_repo.update(event.business_id, event.id, hold)

    assert sweep(testbed) == 0
    testbed.clock.advance(61)
    assert sweep(testbed) == 1


def test_a_message_the_assistant_gave_up_on_reaches_a_person_once() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    post_update(testbed, channel, build_update())
    testbed.run_worker()
    testbed.pipeline.failure = ConflictError("The model is unavailable.")
    post_update(testbed, channel, build_update("Can I bring a dog?", message_id=18))
    testbed.run_worker()
    failed = next(
        event for event in inbox(testbed) if event.status is InboundEventStatus.FAILED
    )

    testbed.clock.advance(HOUR_SECONDS - 60)
    assert sweep(testbed) == 0
    testbed.clock.advance(61)
    assert sweep(testbed) == 1

    [handoff] = testbed.handoffs_to_human.commands
    assert handoff.business_id == business.id
    assert handoff.conversation_id == testbed.pipeline.conversation_id
    assert handoff.reason is HandoffReason.NON_STANDARD_REQUEST
    assert handoff.urgency is HandoffUrgency.HIGH
    assert isinstance(handoff.summary, CodedHandoffSummary)
    assert handoff.summary.code is HandoffSummaryCode.MODEL_UNAVAILABLE
    assert str(handoff.summary.quoted_text) == "Can I bring a dog?"
    marked = testbed.inbound_event_repo.get(failed.business_id, failed.id)
    assert marked is not None
    assert marked.handoff_requested_at == testbed.wall_clock.now_unix()

    testbed.clock.advance(HOUR_SECONDS)
    assert sweep(testbed) == 0
    assert len(testbed.handoffs_to_human.commands) == 1


def test_a_failed_message_without_a_conversation_is_only_marked() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    testbed.pipeline.failure = ConflictError("The assistant is not live.")
    post_update(testbed, channel, build_update())
    testbed.run_worker()

    testbed.clock.advance(HOUR_SECONDS + 1)
    assert sweep(testbed) == 0

    assert testbed.handoffs_to_human.commands == []
    [marked] = inbox(testbed)
    assert marked.handoff_requested_at is not None
