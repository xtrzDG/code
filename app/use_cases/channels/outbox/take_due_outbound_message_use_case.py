import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    decode_outbound_message_payload,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import outbound_serial_key

logger: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_SECOND: int = 1_000_000
# A message waits for an older one to the same recipient at most this long
# past that one's due time; an older message overdue longer than that has
# lost its job (an admin can retry it) and no longer holds the queue.
STALLED_AFTER_SECONDS: int = 10 * 60
# The waiting message comes back just after the older one's next attempt.
FOLLOW_UP_DELAY_SECONDS: int = 1


class TakeDueOutboundMessageUseCase(
    UseCaseContract[QueuedJobInput, OutboundMessageDocument | None]
):
    """
    The outbox message a `deliver_outbound` job names, when it is due:
    PENDING, its next attempt has come, and no older message to the same
    recipient still waits (messages to one customer arrive in the order
    they were queued; a waiting message is queued again for just after the
    older one's next attempt). None when there is nothing to send now.
    """

    def __init__(
        self,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> OutboundMessageDocument | None:
        if input_data.business_id is None:
            logger.warning("Outbox job %s names no business.", input_data.job_id)
            return None

        business_id: BusinessId = input_data.business_id
        message_id: OutboundMessageId = decode_outbound_message_payload(
            input_data.payload
        )
        message: OutboundMessageDocument | None = self._outbound_message_repo.get(
            business_id, message_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        if (
            message is None
            or message.status is not OutboundMessageStatus.PENDING
            or (message.next_attempt_at is not None and message.next_attempt_at > now)
        ):
            # Sent, given up, or its own retry job comes later.
            return None

        older: OutboundMessageDocument | None = self._find_older_waiting(message, now)
        if older is None:
            return message

        due_at: int = max(int(now), int(older.next_attempt_at or now))
        self._job_queue.enqueue(
            DELIVER_OUTBOUND_JOB,
            encode_outbound_message_payload(message.id),
            business_id,
            run_at=Microseconds(
                due_at + FOLLOW_UP_DELAY_SECONDS * MICROSECONDS_PER_SECOND
            ),
            lane=JobLane.OUTBOUND,
            serial_key=outbound_serial_key(business_id, message.recipient_key),
        )
        return None

    def _find_older_waiting(
        self,
        message: OutboundMessageDocument,
        now: Microseconds,
    ) -> OutboundMessageDocument | None:
        stalled_before: int = int(now) - STALLED_AFTER_SECONDS * MICROSECONDS_PER_SECOND
        for waiting in self._outbound_message_repo.list_pending_for_recipient(
            message.business_id, message.recipient_key
        ):
            if not is_queued_before(waiting, message) or is_held(waiting, now):
                continue

            due_at: int = int(waiting.next_attempt_at or waiting.created_at)
            if due_at < stalled_before:
                logger.warning(
                    "Outbox message %s is overdue; later messages no longer wait.",
                    waiting.id,
                )
                continue

            return waiting

        return None


def is_queued_before(
    first: OutboundMessageDocument,
    second: OutboundMessageDocument,
) -> bool:
    return (int(first.created_at), str(first.id)) < (
        int(second.created_at),
        str(second.id),
    )


def is_held(message: OutboundMessageDocument, now: Microseconds) -> bool:
    """
    A staff notification held for quiet hours (never tried, due later):
    an urgent one queued after it goes first.
    """

    return (
        int(message.attempts) == 0
        and message.next_attempt_at is not None
        and message.next_attempt_at > now
    )
