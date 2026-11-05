"""
The outbox's one write path: a message and the job that delivers it are
stored together, and an idempotency key queues a message at most once.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.use_cases.shared.outbox_queue import queue_outbound_message
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
    outbound_serial_key,
)
from tests.channels.outbox_fakes import (
    RecordingJobQueue,
    RecordingOutbox,
    RecordingUnitOfWork,
    VanishingOutbox,
)

NOW: Microseconds = Microseconds(1_790_000_000_000_000)
CHANNEL_ID: ChannelId = ChannelId()
CUSTOMER: ChannelUserId = ChannelUserId("9001")


def reminder(
    business_id: BusinessId,
    key: str = "reminder:booking_1",
    text: str = "See you tomorrow at 19:00.",
    next_attempt_at: Microseconds | None = None,
) -> OutboundMessageDocument:
    idempotency_key = OutboundIdempotencyKey(key)
    return OutboundMessageDocument(
        id=derive_outbound_message_id(business_id, idempotency_key),
        business_id=business_id,
        kind=OutboundMessageKind.BOOKING_REMINDER,
        idempotency_key=idempotency_key,
        recipient_key=customer_recipient_key(CHANNEL_ID, CUSTOMER),
        customer=CustomerRecipient(
            channel_id=CHANNEL_ID,
            channel=ChannelKind.TELEGRAM,
            channel_user_id=CUSTOMER,
        ),
        text=MessageText(text),
        next_attempt_at=next_attempt_at,
        created_at=NOW,
        updated_at=NOW,
    )


def test_a_new_message_and_its_delivery_job_are_written_in_one_unit() -> None:
    unit = RecordingUnitOfWork()
    outbox, queue = RecordingOutbox(unit), RecordingJobQueue(unit)
    business_id = BusinessId()
    message = reminder(business_id)

    stored = queue_outbound_message(outbox, queue, message, unit)

    assert stored == message
    assert outbox.get(business_id, message.id) == message
    [call] = queue.calls
    assert call.job_name == DELIVER_OUTBOUND_JOB
    assert call.payload == encode_outbound_message_payload(message.id)
    assert call.business_id == business_id
    # One recipient's messages leave one at a time, on the outbound lane.
    assert call.lane is JobLane.OUTBOUND
    assert call.serial_key == outbound_serial_key(business_id, message.recipient_key)
    # The message and its job were written inside the same unit, which committed.
    assert outbox.insert_depths == [1]
    assert call.unit_depth == 1
    assert unit.outcomes == ["commit"]


def test_a_message_for_later_is_queued_for_its_attempt_time() -> None:
    queue = RecordingJobQueue()
    later = Microseconds(int(NOW) + 3_600_000_000)

    queue_outbound_message(
        RecordingOutbox(), queue, reminder(BusinessId(), next_attempt_at=later), None
    )

    assert [call.run_at for call in queue.calls] == [later]


def test_a_key_queued_before_is_neither_stored_nor_queued_again() -> None:
    outbox, queue = RecordingOutbox(), RecordingJobQueue()
    business_id = BusinessId()
    first = queue_outbound_message(outbox, queue, reminder(business_id), None)

    # A retried turn builds the same message again, worded differently.
    again = queue_outbound_message(
        outbox, queue, reminder(business_id, text="Reminder: tomorrow, 19:00."), None
    )

    assert again == first
    assert again.text == MessageText("See you tomorrow at 19:00.")
    assert len(queue.calls) == 1


def test_the_same_key_in_two_businesses_is_two_messages() -> None:
    outbox, queue = RecordingOutbox(), RecordingJobQueue()

    first = queue_outbound_message(outbox, queue, reminder(BusinessId()), None)
    second = queue_outbound_message(outbox, queue, reminder(BusinessId()), None)

    assert first.id != second.id
    assert len(queue.calls) == 2


def test_a_taken_key_whose_row_is_gone_returns_the_message_without_a_job() -> None:
    queue = RecordingJobQueue()
    message = reminder(BusinessId())

    stored = queue_outbound_message(VanishingOutbox(), queue, message, None)

    assert stored == message
    assert queue.calls == []


def test_a_job_that_cannot_be_queued_rolls_the_message_back_with_it() -> None:
    unit = RecordingUnitOfWork()
    refused = ExternalServiceError("the job queue is unreachable")
    outbox = RecordingOutbox(unit)

    with pytest.raises(ExternalServiceError):
        queue_outbound_message(
            outbox, RecordingJobQueue(unit, refused), reminder(BusinessId()), unit
        )

    # The insert ran inside the unit that rolled back: no message without a job.
    assert outbox.insert_depths == [1]
    assert unit.outcomes == ["rollback"]
