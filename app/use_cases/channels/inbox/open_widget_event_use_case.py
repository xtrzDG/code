from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.deliveries import InboundEventClaim
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.deliveries.constrained_integers import (
    InboundProcessingAttemptCount,
)
from app.use_cases.channels.inbox.inbox_queue import queue_inbound_job
from app.utilities.deliveries.delivery_jobs import PROCESS_INBOUND_MESSAGE_JOB
from app.utilities.deliveries.delivery_keys import (
    derive_inbound_event_id,
    inbound_serial_key,
    new_provider_message_id,
)
from app.utilities.deliveries.inbound_claims import inbound_lease_end
from app.utilities.deliveries.inbox_messages import build_inbound_customer_message


class OpenWidgetEventUseCase(UseCaseContract[InboundMessage, InboundEventClaim]):
    """
    The website widget answers its visitor in the same request, but writes
    the message into the inbox first, held by this request until its lease
    ends, and queues `process_inbound_message` for that moment: when the
    request finishes the job finds the event answered; when the server
    died mid-turn the worker answers instead, and the widget's polling
    shows the reply.
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

    def run(self, input_data: InboundMessage) -> InboundEventClaim:
        now: Microseconds = self._wall_clock.now_unix()
        provider_message_id: ProviderMessageId = new_provider_message_id()
        event = InboundEventDocument(
            id=derive_inbound_event_id(
                input_data.business_id, input_data.channel, provider_message_id
            ),
            business_id=input_data.business_id,
            kind=InboundEventKind.CUSTOMER_MESSAGE,
            channel=input_data.channel,
            provider_message_id=provider_message_id,
            customer_message=build_inbound_customer_message(
                input_data.channel_user_id,
                input_data.text,
                input_data.contact_name,
                input_data.contact_phone_number,
            ),
            status=InboundEventStatus.PROCESSING,
            attempts=InboundProcessingAttemptCount(1),
            lease_until=inbound_lease_end(now),
            created_at=now,
            updated_at=now,
        )
        self._inbound_event_repo.insert_if_new(event)
        queue_inbound_job(
            self._job_queue,
            event,
            PROCESS_INBOUND_MESSAGE_JOB,
            inbound_serial_key(
                input_data.business_id,
                input_data.channel,
                str(input_data.channel_user_id),
            ),
            run_at=event.lease_until,
        )
        return InboundEventClaim(
            event=event,
            message=input_data.model_copy(
                update={
                    "customer_message_id": event.customer_message_id,
                    "reply_message_id": event.reply_message_id,
                }
            ),
        )
