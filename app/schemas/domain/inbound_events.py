from typing import Self

from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field, model_validator
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, InboundContextNote
from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.deliveries.constrained_integers import (
    InboundProcessingAttemptCount,
)
from app.schemas.typings.deliveries.prefixed_id import InboundEventId, OutboundMessageId
from app.schemas.typings.deliveries.strings import InboundErrorText, InboundPayloadText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag


class InboundCustomerMessage(PersistentDocument):
    """
    A customer's message as the channel adapter read it from the webhook:
    the typed text and the attachments (voice notes, photos, places, ...),
    whose files the worker fetches. `acquisition_source` is where the
    customer came from when the message carried it (a tagged link, an ad):
    a conversation this message starts keeps it. `context_note` is what
    the message refers to that the assistant cannot see (a reply to the
    business's Instagram story, a story mention).
    """

    channel_user_id: ChannelUserId
    text: MessageText
    contact_name: ContactName | None = None
    contact_phone_number: E164PhoneNumber | None = None
    attachments: list[InboundAttachment] = Field(
        default_factory=list[InboundAttachment]
    )
    acquisition_source: AcquisitionSourceTag | None = None
    context_note: InboundContextNote | None = None


class InboundEventDocument(BaseDocument):
    """
    One message a platform delivered, kept until it is processed (the inbox
    of reliability: a webhook is acknowledged as soon as its event is
    stored, and the worker does the slow work).

    The id is derived from the business, the channel and the platform's own
    message id, so a redelivered webhook finds its event instead of making a
    second one. The ids of the customer's message and of the assistant's
    reply are chosen here, once: a turn that runs again after a crash stores
    the same two transcript messages, and a reply that was already stored is
    sent instead of generated again.

    `business_id` is None for platform events (the staff bot, finished-call
    reports before their business is found). `payload` keeps the verified
    body of those events until the worker reads it.

    Version 2: the attachments of the customer message (optional, so
    version 1 rows read as they are).

    Version 3: when staff were asked to answer a customer message the
    assistant never answered (`handoff_requested_at`, set by the sweeper of
    the inbox once per FAILED event; optional).

    Version 4: the customer message's `acquisition_source` (optional).

    Version 5: `customer_channel_user_id`, the sender of the customer
    message kept beside it (filled from it when missing, so older rows read
    the same), for erasure to find a customer's events by an index.

    Version 6: `holder_job_id`, the queued job that last took the event
    (optional). The queue runs a job in one place at a time, so a later
    attempt of that same job (its worker died) takes the event over at
    once instead of waiting out the processing lease.

    Version 7: the customer message's `context_note` (optional).
    """

    schema_version: SchemaVersion = SchemaVersion("7")
    id: InboundEventId
    business_id: BusinessId | None = None
    kind: InboundEventKind
    channel: ChannelKind
    channel_id: ChannelId | None = None
    provider_message_id: ProviderMessageId
    customer_message: InboundCustomerMessage | None = None
    payload: InboundPayloadText | None = Field(default=None, repr=False)
    customer_message_id: MessageId = Field(default_factory=MessageId)
    reply_message_id: MessageId = Field(default_factory=MessageId)
    status: InboundEventStatus = InboundEventStatus.RECEIVED
    attempts: InboundProcessingAttemptCount = InboundProcessingAttemptCount(0)
    lease_until: Microseconds | None = None
    last_error: InboundErrorText | None = None
    conversation_id: ConversationId | None = None
    outbound_message_id: OutboundMessageId | None = None
    processed_at: Microseconds | None = None
    handoff_requested_at: Microseconds | None = None
    customer_channel_user_id: ChannelUserId | None = None
    holder_job_id: QueuedJobId | None = None

    @model_validator(mode="after")
    def copy_customer_sender(self) -> Self:
        """The lookup copy of the customer message's sender, when missing."""

        if self.customer_channel_user_id is None and self.customer_message is not None:
            self.customer_channel_user_id = self.customer_message.channel_user_id

        return self
