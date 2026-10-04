"""
The WhatsApp leg of a text-back: the owner's approved template from the
business's number, queued in the outbox (once per missed call) and sent by
the worker with retries. The outbox wakes the text-back job again when the
template was delivered or refused for good.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
    OutboundTemplate,
)
from app.schemas.exceptions.application_errors import (
    DeliveryNotConfiguredError,
    ProviderRejectedMessageError,
)
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.use_cases.shared.outbox_queue import queue_outbound_message
from app.use_cases.voice.missed_calls.text_back_conversation import whatsapp_user_id
from app.use_cases.voice.missed_calls.text_back_rules import text_back_deadline
from app.utilities.calls.text_back_texts import TEXT_BACK_MESSAGE_TEXT
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.language_codes import to_whatsapp_template_language
from app.utilities.deliveries.customer_message_keys import text_back_idempotency_key
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
)


@dataclass(frozen=True)
class TextBackWhatsApp:
    """Queues the template and reads how its delivery went."""

    channel_repo: ChannelRepoContract
    outbound_message_repo: OutboundMessageRepoContract
    job_queue: JobQueueFacilitatorContract
    unit_of_work: StorageUnitOfWorkContract | None
    text_resolver: LocalizedTextResolverContract

    def queued(self, missed: MissedCallDocument) -> OutboundMessageDocument | None:
        """The text-back's outbox message, once it was queued."""

        idempotency_key = text_back_idempotency_key(missed.id)
        return self.outbound_message_repo.get(
            missed.business_id,
            derive_outbound_message_id(missed.business_id, idempotency_key),
        )

    def text(
        self, business: BusinessDocument, missed: MissedCallDocument
    ) -> MessageText:
        """What the template says, as the conversation it opens shows it."""

        return MessageText(
            str(
                self.text_resolver.resolve(TEXT_BACK_MESSAGE_TEXT, missed.language)
            ).format(business=business.name)
        )

    def queue(
        self,
        business: BusinessDocument,
        missed: MissedCallDocument,
        caller: E164PhoneNumber,
        template_name: WhatsAppTemplateName | None,
        now: Microseconds,
    ) -> None:
        """
        Queue the template in the caller's language (English when Meta has
        no such translation), its parameter the business name. Raises
        DeliveryNotConfiguredError without a template and
        ProviderRejectedMessageError without a connected WhatsApp number:
        both are refusals for good (the SMS may follow).
        """

        if template_name is None:
            raise DeliveryNotConfiguredError("No WhatsApp template for text-backs.")

        channel: ChannelDocument | None = find_business_channel(
            self.channel_repo, business.id, ChannelKind.WHATSAPP
        )
        if channel is None or not is_channel_active(channel):
            raise ProviderRejectedMessageError(
                "The WhatsApp number of this business is not connected."
            )

        idempotency_key = text_back_idempotency_key(missed.id)
        recipient: ChannelUserId = whatsapp_user_id(caller)
        queue_outbound_message(
            self.outbound_message_repo,
            self.job_queue,
            OutboundMessageDocument(
                id=derive_outbound_message_id(business.id, idempotency_key),
                business_id=business.id,
                kind=OutboundMessageKind.TEXT_BACK,
                idempotency_key=idempotency_key,
                recipient_key=customer_recipient_key(channel.id, recipient),
                customer=CustomerRecipient(
                    channel_id=channel.id,
                    channel=ChannelKind.WHATSAPP,
                    channel_user_id=recipient,
                ),
                text=self.text(business, missed),
                template=OutboundTemplate(
                    name=template_name,
                    language_code=to_whatsapp_template_language(missed.language),
                    body_parameters=[MessageText(str(business.name))],
                ),
                missed_call_id=missed.id,
                send_before=text_back_deadline(missed.called_at),
                created_at=now,
                updated_at=now,
            ),
            self.unit_of_work,
        )
