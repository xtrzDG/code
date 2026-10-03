from contextlib import AbstractContextManager, nullcontext

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.channels.widget_turns import WidgetMessageAcceptedView
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.channels.strings import ProviderMessageId
from app.use_cases.shared.inbox_queue import queue_inbound_job
from app.utilities.deliveries.delivery_jobs import PROCESS_INBOUND_MESSAGE_JOB
from app.utilities.deliveries.delivery_keys import (
    derive_inbound_event_id,
    inbound_serial_key,
    new_provider_message_id,
)
from app.utilities.deliveries.inbox_messages import build_inbound_customer_message


class QueueWidgetMessageUseCase(
    UseCaseContract[InboundMessage, WidgetMessageAcceptedView]
):
    """
    A website widget message goes the way of every channel's message: into
    the inbox, with `process_inbound_message` queued on the inbound lane
    (one visitor's messages one at a time, oldest first) in the same
    storage transaction, so neither exists without the other. A worker
    answers it within moments (the queue wakes it through NOTIFY) and the
    widget's polling shows the answer.

    The request thread never waits for the model, so a burst of visitors or
    a slow provider cannot take the API's threads or database connections.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work

    def run(self, input_data: InboundMessage) -> WidgetMessageAcceptedView:
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
            created_at=now,
            updated_at=now,
        )
        with self._transaction():
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
            )

        return WidgetMessageAcceptedView(event_id=event.id)

    def _transaction(self) -> AbstractContextManager[None]:
        if self._unit_of_work is None:
            return nullcontext()

        return self._unit_of_work.unit_of_work()
