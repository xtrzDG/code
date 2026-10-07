from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.delivery_repositories import (
    InboundEventRepoContract,
    OutboundMessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.deliveries import (
    InboundEventKind,
    InboundEventStatus,
    OutboundMessageKind,
    OutboundMessageStatus,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
)
from app.schemas.dto.deliveries import InboundAnswer
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.utilities.channels.channel_activity import (
    stamp_business_channel_activity,
)
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
    outbound_serial_key,
    reply_idempotency_key,
)


class FinishInboundEventUseCase(
    UseCaseContract[InboundAnswer, InboundEventDocument | None]
):
    """
    Close a processed inbox event. A reply in a messaging channel goes into
    the outbox first (one message per stored reply, sent by
    `deliver_outbound` with retries); the widget's reply is already stored
    for it. The event becomes ANSWERED, or HANDED_OFF when the assistant
    stayed silent because staff own the conversation.

    Queuing the reply again is harmless (the outbox keeps one message per
    reply), so an event whose worker died at any step can be processed
    again. A widget answer is the website chat's outgoing message: the
    channel notes when (`last_outbound_at`, to the minute); the outbox
    notes it for the other channels once delivered.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        channel_repo: ChannelRepoContract,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: InboundAnswer) -> InboundEventDocument | None:
        event: InboundEventDocument = input_data.event
        now: Microseconds = self._wall_clock.now_unix()
        outbound_message_id: OutboundMessageId | None = None
        if (
            input_data.text is not None
            and event.business_id is not None
            and event.channel_id is not None
            and event.customer_message is not None
        ):
            outbound_message_id = self._queue_reply(
                input_data,
                CustomerRecipient(
                    channel_id=event.channel_id,
                    channel=event.channel,
                    channel_user_id=event.customer_message.channel_user_id,
                ),
                event.business_id,
                input_data.text,
                now,
            )

        is_silent: bool = (
            event.kind is InboundEventKind.CUSTOMER_MESSAGE and input_data.text is None
        )

        def finish(current: InboundEventDocument) -> InboundEventDocument:
            current.status = (
                InboundEventStatus.HANDED_OFF
                if is_silent
                else InboundEventStatus.ANSWERED
            )
            current.lease_until = None
            current.last_error = None
            current.conversation_id = input_data.conversation_id
            current.outbound_message_id = outbound_message_id
            current.processed_at = now
            current.updated_at = now
            return current

        finished: InboundEventDocument | None = self._inbound_event_repo.update(
            event.business_id, event.id, finish
        )
        if (
            event.channel is ChannelKind.WEB_CHAT
            and input_data.text is not None
            and event.business_id is not None
        ):
            stamp_business_channel_activity(
                self._channel_repo,
                event.business_id,
                ChannelKind.WEB_CHAT,
                MessageDirection.OUTBOUND,
                now,
            )

        return finished

    def _queue_reply(
        self,
        answer: InboundAnswer,
        recipient: CustomerRecipient,
        business_id: BusinessId,
        text: MessageText,
        now: Microseconds,
    ) -> OutboundMessageId:
        event: InboundEventDocument = answer.event
        idempotency_key: OutboundIdempotencyKey = reply_idempotency_key(
            answer.conversation_id, event.reply_message_id
        )
        recipient_key: OutboundRecipientKey = customer_recipient_key(
            recipient.channel_id, recipient.channel_user_id
        )
        message = OutboundMessageDocument(
            id=derive_outbound_message_id(business_id, idempotency_key),
            business_id=business_id,
            kind=OutboundMessageKind.CUSTOMER_REPLY,
            idempotency_key=idempotency_key,
            recipient_key=recipient_key,
            customer=recipient,
            text=text,
            choices=answer.choices,
            conversation_id=answer.conversation_id,
            source_message_id=event.reply_message_id,
            created_at=now,
            updated_at=now,
        )
        if not self._outbound_message_repo.insert_if_new(message):
            stored: OutboundMessageDocument | None = self._outbound_message_repo.get(
                business_id, message.id
            )
            if stored is None or stored.status is not OutboundMessageStatus.PENDING:
                return message.id

        self._job_queue.enqueue(
            DELIVER_OUTBOUND_JOB,
            encode_outbound_message_payload(message.id),
            business_id,
            lane=JobLane.OUTBOUND,
            serial_key=outbound_serial_key(business_id, recipient_key),
        )
        return message.id
