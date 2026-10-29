"""
A later attempt of the job that holds an inbox message takes it over at
once: the queue hands a job out again only after its earlier attempt is
over (here, its worker died). Any other job waits for the processing lease.
"""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.delivery_repositories import InboundEventRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.constrained_integers import (
    MessageCoalesceSeconds,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.use_cases.channels.inbox.claim_inbound_burst_use_case import (
    ClaimInboundBurstUseCase,
)
from app.utilities.deliveries.delivery_jobs import (
    PROCESS_INBOUND_MESSAGE_JOB,
    encode_inbound_event_payload,
)
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id
from app.utilities.deliveries.inbound_bursts import select_burst
from app.utilities.deliveries.inbound_claims import (
    INBOUND_PROCESSING_LEASE_SECONDS,
    take_inbound_event,
)
from tests.channels.outbox_fakes import RecordingJobQueue
from tests.platform.worker_fakes import ControlledClock

SECOND: int = 1_000_000
BUSINESS: BusinessId = BusinessId()
CHANNEL: ChannelId = ChannelId()
FIRST_JOB: QueuedJobId = QueuedJobId()
OTHER_JOB: QueuedJobId = QueuedJobId()


def customer_event(number: int, created_at: Microseconds) -> InboundEventDocument:
    provider_message_id = ProviderMessageId(f"update_{number}")
    return InboundEventDocument(
        id=derive_inbound_event_id(BUSINESS, ChannelKind.TELEGRAM, provider_message_id),
        business_id=BUSINESS,
        kind=InboundEventKind.CUSTOMER_MESSAGE,
        channel=ChannelKind.TELEGRAM,
        channel_id=CHANNEL,
        provider_message_id=provider_message_id,
        customer_message=InboundCustomerMessage(
            channel_user_id=ChannelUserId("9001"), text=MessageText("A table?")
        ),
        created_at=created_at,
        updated_at=created_at,
    )


def later(now: Microseconds, seconds: int) -> Microseconds:
    return Microseconds(int(now) + seconds * SECOND)


def job_input(job_id: QueuedJobId, event: InboundEventDocument) -> QueuedJobInput:
    return QueuedJobInput(
        job_id=job_id,
        job_name=PROCESS_INBOUND_MESSAGE_JOB,
        payload=encode_inbound_event_payload(event.id),
        business_id=BUSINESS,
    )


def test_the_holding_job_takes_its_message_over_at_once() -> None:
    now = ControlledClock().wall_clock().now_unix()
    taken = take_inbound_event(customer_event(1, now), now, FIRST_JOB)
    assert taken is not None
    assert taken.holder_job_id == FIRST_JOB

    again = take_inbound_event(taken, later(now, 121), FIRST_JOB)

    assert again is not None
    assert again.status is InboundEventStatus.PROCESSING
    assert again.attempts == 2
    assert again.lease_until == later(now, 121 + INBOUND_PROCESSING_LEASE_SECONDS)


def test_another_job_waits_for_the_processing_lease() -> None:
    now = ControlledClock().wall_clock().now_unix()
    taken = take_inbound_event(customer_event(1, now), now, FIRST_JOB)
    assert taken is not None

    assert take_inbound_event(taken, later(now, 121), OTHER_JOB) is None
    after_lease = take_inbound_event(
        taken, later(now, INBOUND_PROCESSING_LEASE_SECONDS + 1), OTHER_JOB
    )
    assert after_lease is not None
    assert after_lease.holder_job_id == OTHER_JOB


def test_a_finished_message_is_never_taken_again() -> None:
    now = ControlledClock().wall_clock().now_unix()
    taken = take_inbound_event(customer_event(1, now), now, FIRST_JOB)
    assert taken is not None
    taken.status = InboundEventStatus.ANSWERED

    assert take_inbound_event(taken, later(now, 1), FIRST_JOB) is None


def test_a_burst_keeps_the_messages_its_own_job_held() -> None:
    now = ControlledClock().wall_clock().now_unix()
    trigger = customer_event(1, now)
    earlier = take_inbound_event(customer_event(2, later(now, -2)), now, FIRST_JOB)
    assert earlier is not None

    own = select_burst(trigger, [earlier], later(now, 1), FIRST_JOB)
    other = select_burst(trigger, [earlier], later(now, 1), OTHER_JOB)

    assert [event.id for event in own] == [earlier.id, trigger.id]
    assert [event.id for event in other] == [trigger.id]


def test_the_claim_takes_over_for_its_job_and_queues_the_others_for_later() -> None:
    clock = ControlledClock()
    repo = InboundEventRepository(
        InMemoryDocumentCollectionAdapter(InboundEventDocument)
    )
    jobs = RecordingJobQueue()
    claim = ClaimInboundBurstUseCase(
        repo, jobs, clock.wall_clock(), MessageCoalesceSeconds(0)
    )
    event = customer_event(1, clock.wall_clock().now_unix())
    repo.insert_if_new(event)
    first = claim.run(job_input(FIRST_JOB, event))
    assert first is not None
    assert len(first.claims) == 1  # and then its worker died

    clock.advance(121)
    other = claim.run(job_input(OTHER_JOB, event))
    again = claim.run(job_input(FIRST_JOB, event))

    assert other is None
    held = first.claims[0].event
    assert [call.run_at for call in jobs.calls] == [held.lease_until]
    assert again is not None
    assert [item.event.id for item in again.claims] == [event.id]
    assert again.claims[0].event.attempts == 2
