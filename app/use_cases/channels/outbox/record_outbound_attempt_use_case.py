import logging
import random
from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.notifications import StaffDeliveryRecorderContract
from app.contracts.repositories.booking_repositories import HandoffRepoContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.deliveries import OutboundAttempt
from app.schemas.typings.deliveries.constrained_integers import DeliveryAttemptCount
from app.use_cases.channels.outbox.customer_message_follow_ups import (
    announce_staff_reply_delivery,
    continue_text_back,
)
from app.use_cases.channels.outbox.delivery_follow_ups import (
    update_channel_health,
    update_feedback_request,
    update_handoff_notification,
)
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import outbound_serial_key
from app.utilities.deliveries.retry_policy import is_retryable, retry_delay_seconds

logger: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000


class RecordOutboundAttemptUseCase(
    UseCaseContract[OutboundAttempt, OutboundMessageDocument | None]
):
    """
    Store what a send attempt did. Delivered: DELIVERED with the platform's
    message id. A temporary failure (5xx, timeout, 429) before the last
    attempt: PENDING again with the next attempt after an exponential
    backoff with jitter, never sooner than the platform's Retry-After, and
    a job queued for that moment (queued first, so a waiting message always
    has its job). A refusal, a missing provider or the last attempt: DEAD.

    The channel's health follows its replies (`update_channel_health`), a
    handoff follows its notifications (`update_handoff_notification`), a
    feedback request its message (`update_feedback_request`), a staff
    contact's or device's delivery state follows its own, open cabinets
    hear about a staff reply's state, and a missed call's text-back goes on
    once its WhatsApp template is settled.
    """

    def __init__(
        self,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        channel_repo: ChannelRepoContract,
        handoff_repo: HandoffRepoContract,
        live_events: EventPublisherFacilitatorContract,
        delivery_recorder: StaffDeliveryRecorderContract,
        feedback_request_repo: FeedbackRequestRepoContract,
        # Spreads retry times only; nothing secret depends on it.
        jitter: Callable[[], float] = random.random,  # nosec B311
    ) -> None:
        self._feedback_request_repo: FeedbackRequestRepoContract = feedback_request_repo
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._channel_repo: ChannelRepoContract = channel_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._delivery_recorder: StaffDeliveryRecorderContract = delivery_recorder
        self._jitter: Callable[[], float] = jitter

    def run(self, input_data: OutboundAttempt) -> OutboundMessageDocument | None:
        message: OutboundMessageDocument = input_data.message
        now: Microseconds = input_data.attempted_at
        attempts = DeliveryAttemptCount(int(message.attempts) + 1)
        next_attempt_at: Microseconds | None = None
        if input_data.failure is not None and is_retryable(
            input_data.failure, attempts
        ):
            delay: int = retry_delay_seconds(
                attempts, input_data.retry_after_seconds, self._jitter()
            )
            next_attempt_at = Microseconds(int(now) + delay * MICROSECONDS_PER_SECOND)
            self._job_queue.enqueue(
                DELIVER_OUTBOUND_JOB,
                encode_outbound_message_payload(message.id),
                message.business_id,
                run_at=next_attempt_at,
                lane=JobLane.OUTBOUND,
                serial_key=outbound_serial_key(
                    message.business_id, message.recipient_key
                ),
            )

        def record(current: OutboundMessageDocument) -> OutboundMessageDocument | None:
            if current.status is not OutboundMessageStatus.PENDING:
                return None

            current.attempts = attempts
            current.delivered_parts = input_data.delivered_parts
            current.provider_message_id = input_data.provider_message_id
            current.updated_at = now
            current.next_attempt_at = next_attempt_at
            if input_data.failure is None:
                current.status = OutboundMessageStatus.DELIVERED
                current.delivered_at = now
                current.last_error = None
                current.last_failure_reason = None
            else:
                current.last_error = input_data.error
                current.last_failure_reason = input_data.reason
                if next_attempt_at is None:
                    current.status = OutboundMessageStatus.DEAD

            return current

        stored: OutboundMessageDocument | None = self._outbound_message_repo.update(
            message.business_id, message.id, record
        )
        if stored is None:
            return None

        if stored.status is OutboundMessageStatus.DEAD:
            logger.warning(
                "Outbox message %s (%s) was given up after %d attempt(s): %s",
                stored.id,
                stored.kind.value,
                int(stored.attempts),
                stored.last_error,
            )

        update_channel_health(
            self._channel_repo, self._live_events, stored, input_data, now
        )
        update_handoff_notification(self._handoff_repo, stored, now)
        update_feedback_request(self._feedback_request_repo, stored, now)
        self._delivery_recorder.record(stored)
        announce_staff_reply_delivery(self._live_events, stored)
        continue_text_back(self._job_queue, stored)
        return stored
