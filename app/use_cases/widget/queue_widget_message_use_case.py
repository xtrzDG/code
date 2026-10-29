from contextlib import AbstractContextManager, nullcontext

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.repositories.media_repositories import WidgetUploadRepoContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.constants.media import WidgetUploadRefusal
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.channels.widget_turns import WidgetMessageAcceptedView
from app.schemas.dto.channels.widget_uploads import AcceptedWidgetMessage
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.use_cases.shared.inbox_queue import queue_inbound_job
from app.utilities.channels.widget_visitors import widget_visitor_id
from app.utilities.deliveries.delivery_jobs import PROCESS_INBOUND_MESSAGE_JOB
from app.utilities.deliveries.delivery_keys import (
    derive_inbound_event_id,
    inbound_serial_key,
    new_provider_message_id,
)
from app.utilities.deliveries.inbox_messages import build_inbound_customer_message
from app.utilities.media.upload_refusals import upload_refused


class QueueWidgetMessageUseCase(
    UseCaseContract[AcceptedWidgetMessage, WidgetMessageAcceptedView]
):
    """
    A website widget message goes the way of every channel's message: into
    the inbox, with `process_inbound_message` queued on the inbound lane
    (one visitor's messages one at a time, oldest first) in the same
    storage transaction, so neither exists without the other. A worker
    answers it within moments (the queue wakes it through NOTIFY) and the
    widget's polling shows the answer.

    The photos and voice notes the message names are claimed in the same
    transaction, each once and only by its own visitor: of two messages
    naming one upload, one is queued and the other is refused (422
    `attachment_already_sent`: the upload went with the first), and the
    worker reads each file the way it downloads a messenger's.

    The request thread never waits for the model, so a burst of visitors or
    a slow provider cannot take the API's threads or database connections.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        widget_upload_repo: WidgetUploadRepoContract,
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._widget_upload_repo: WidgetUploadRepoContract = widget_upload_repo
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work

    def run(self, input_data: AcceptedWidgetMessage) -> WidgetMessageAcceptedView:
        accepted: AcceptedWidgetMessage = input_data
        message: InboundMessage = accepted.message
        now: Microseconds = self._wall_clock.now_unix()
        provider_message_id: ProviderMessageId = new_provider_message_id()
        event = InboundEventDocument(
            id=derive_inbound_event_id(
                message.business_id, message.channel, provider_message_id
            ),
            business_id=message.business_id,
            kind=InboundEventKind.CUSTOMER_MESSAGE,
            channel=message.channel,
            provider_message_id=provider_message_id,
            customer_message=build_inbound_customer_message(
                message.channel_user_id,
                message.text,
                message.contact_name,
                message.contact_phone_number,
                attachments=accepted.attachments,
                acquisition_source=message.acquisition_source,
            ),
            created_at=now,
            updated_at=now,
        )
        with self._transaction():
            self._claim_uploads(accepted, now)
            self._inbound_event_repo.insert_if_new(event)
            queue_inbound_job(
                self._job_queue,
                event,
                PROCESS_INBOUND_MESSAGE_JOB,
                inbound_serial_key(
                    message.business_id,
                    message.channel,
                    str(message.channel_user_id),
                ),
            )

        return WidgetMessageAcceptedView(event_id=event.id)

    def _claim_uploads(
        self, accepted: AcceptedWidgetMessage, now: Microseconds
    ) -> None:
        """
        Each named upload for this message, or none of them: a claim that
        loses gives back the ones before it (a Postgres transaction rolls
        them back anyway; the in-memory storage has no transaction).
        """

        message: InboundMessage = accepted.message
        visitor = widget_visitor_id(str(message.channel_user_id))
        claimed: list[WidgetUploadId] = []
        for upload_id in accepted.upload_ids:
            if (
                self._widget_upload_repo.claim(
                    message.business_id, upload_id, visitor, now
                )
                is None
            ):
                for claimed_id in claimed:
                    self._widget_upload_repo.release(message.business_id, claimed_id)
                raise upload_refused(
                    WidgetUploadRefusal.ATTACHMENT_ALREADY_SENT, upload_id
                )

            claimed.append(upload_id)

    def _transaction(self) -> AbstractContextManager[None]:
        if self._unit_of_work is None:
            return nullcontext()

        return self._unit_of_work.unit_of_work()
