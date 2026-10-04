import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.deliveries import InboundEventClaim
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.typings.deliveries.prefixed_id import InboundEventId
from app.schemas.typings.platform.constrained_strings import JobSerialKey
from app.use_cases.shared.inbox_queue import queue_inbound_job
from app.utilities.deliveries.delivery_jobs import decode_inbound_event_payload
from app.utilities.deliveries.delivery_keys import inbound_serial_key
from app.utilities.deliveries.inbound_claims import (
    is_inbound_event_finished,
    is_inbound_event_held,
    take_inbound_event,
)
from app.utilities.deliveries.inbox_messages import customer_written_text

logger: logging.Logger = logging.getLogger(__name__)


class ClaimInboundEventUseCase(
    UseCaseContract[QueuedJobInput, InboundEventClaim | None]
):
    """
    Take the inbox event a processing job names, held by this worker until
    its lease ends (one more attempt). None when there is nothing to do: the
    event is finished or gone, or another processing still holds it (a
    widget request, or a worker whose lease has not run out); the job then
    comes back when that lease ends, so a crashed turn is processed again.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> InboundEventClaim | None:
        event_id: InboundEventId = decode_inbound_event_payload(input_data.payload)
        now: Microseconds = self._wall_clock.now_unix()
        stored: InboundEventDocument | None = self._inbound_event_repo.get(
            input_data.business_id, event_id
        )
        if stored is None:
            logger.warning("Inbox event %s was not found.", event_id)
            return None

        if is_inbound_event_finished(stored):
            return None

        if is_inbound_event_held(stored, now):
            queue_inbound_job(
                self._job_queue,
                stored,
                input_data.job_name,
                serial_key_of(stored),
                run_at=stored.lease_until,
            )
            return None

        claimed: InboundEventDocument | None = self._inbound_event_repo.update(
            input_data.business_id,
            event_id,
            lambda current: take_inbound_event(current, now),
        )
        if claimed is None:
            return None

        return InboundEventClaim(
            event=claimed,
            message=build_inbound_message(claimed),
            is_final_attempt=input_data.is_final_attempt,
        )


def build_inbound_message(event: InboundEventDocument) -> InboundMessage | None:
    """The engine's InboundMessage of a customer event, with the inbox's ids."""

    customer: InboundCustomerMessage | None = event.customer_message
    if (
        event.kind is not InboundEventKind.CUSTOMER_MESSAGE
        or customer is None
        or event.business_id is None
    ):
        return None

    return InboundMessage(
        business_id=event.business_id,
        channel=event.channel,
        channel_user_id=customer.channel_user_id,
        text=customer_written_text(customer),
        contact_name=customer.contact_name,
        contact_phone_number=customer.contact_phone_number,
        customer_message_id=event.customer_message_id,
        reply_message_id=event.reply_message_id,
        acquisition_source=customer.acquisition_source,
    )


def serial_key_of(event: InboundEventDocument) -> JobSerialKey | None:
    """The serial key a customer's events are processed under (in order)."""

    if event.customer_message is None:
        return None

    return inbound_serial_key(
        event.business_id,
        event.channel,
        str(event.customer_message.channel_user_id),
    )
