"""
Sending a message the business starts: the outbox message that carries it
(free text, or the WhatsApp template with its parameters) and the
conversation that shows it, where the customer's answer then lands. The
message is written as the business's (staff), so the assistant sees what
the customer was told when they answer.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
    OutboundTemplate,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.shared.outbox_queue import queue_outbound_message
from app.use_cases.shared.proactive_routes import ProactiveRoute
from app.utilities.channels.language_codes import to_whatsapp_template_language
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
# A customer message within a day joins the conversation it continues.
CONVERSATION_WINDOW: timedelta = timedelta(hours=24)


@dataclass(frozen=True)
class ProactiveLetter:
    """
    A message ready to go: its text, the parameters of its WhatsApp template
    (used outside the 24-hour window), its language, the key that queues it
    once, and when it is no longer worth sending (None: any time).
    """

    text: MessageText
    language: LanguageTag
    idempotency_key: OutboundIdempotencyKey
    template_parameters: list[MessageText] = field(default_factory=list[MessageText])
    send_before: Microseconds | None = None


@dataclass(frozen=True)
class ProactiveSender:
    outbound_message_repo: OutboundMessageRepoContract
    job_queue: JobQueueFacilitatorContract
    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    unit_of_work: StorageUnitOfWorkContract | None

    def queue(
        self,
        business: BusinessDocument,
        route: ProactiveRoute,
        letter: ProactiveLetter,
        conversation_id: ConversationId | None,
        now: Microseconds,
    ) -> OutboundMessageId:
        """The outbox message and its delivery job (once per idempotency key)."""

        template: OutboundTemplate | None = (
            None
            if route.template_name is None
            else OutboundTemplate(
                name=route.template_name,
                language_code=to_whatsapp_template_language(letter.language),
                body_parameters=list(letter.template_parameters),
            )
        )
        message: OutboundMessageDocument = queue_outbound_message(
            self.outbound_message_repo,
            self.job_queue,
            OutboundMessageDocument(
                id=derive_outbound_message_id(business.id, letter.idempotency_key),
                business_id=business.id,
                kind=OutboundMessageKind.CUSTOMER_REPLY,
                idempotency_key=letter.idempotency_key,
                recipient_key=customer_recipient_key(
                    route.channel.id, route.identity.channel_user_id
                ),
                customer=CustomerRecipient(
                    channel_id=route.channel.id,
                    channel=route.identity.channel,
                    channel_user_id=route.identity.channel_user_id,
                ),
                text=letter.text,
                template=template,
                conversation_id=conversation_id,
                send_before=letter.send_before,
                created_at=now,
                updated_at=now,
            ),
            self.unit_of_work,
        )
        return message.id

    def show(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        route: ProactiveRoute,
        letter: ProactiveLetter,
        now: Microseconds,
    ) -> ConversationId | None:
        """
        The message as the newest of the customer's conversation in that
        messenger (an open one of the last day, else a new one pinned to the
        live version; None while the business has none).
        """

        conversation: ConversationDocument | None = self._open_conversation(
            business, contact, route, letter.language, now
        )
        if conversation is None:
            return None

        conversation.last_message_at = now
        conversation.updated_at = now
        self.conversation_repo.save(conversation)
        self.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=business.id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.STAFF,
                text=letter.text,
                language=letter.language,
                channel=route.identity.channel,
                created_at=now,
                updated_at=now,
            )
        )
        return conversation.id

    def _open_conversation(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        route: ProactiveRoute,
        language: LanguageTag,
        now: Microseconds,
    ) -> ConversationDocument | None:
        window_start = Microseconds(
            int(now)
            - int(CONVERSATION_WINDOW.total_seconds()) * MICROSECONDS_PER_SECOND
        )
        for conversation in self.conversation_repo.list_by_contact(
            business.id, contact.id, last_message_from=window_start
        ):
            if (
                conversation.channel is route.identity.channel
                and conversation.channel_user_id == route.identity.channel_user_id
                and not conversation.is_sandbox
                and conversation.status is not ConversationStatus.CLOSED
            ):
                return conversation

        if business.published_assistant_version_id is None:
            return None

        return ConversationDocument(
            business_id=business.id,
            contact_id=contact.id,
            assistant_version_id=business.published_assistant_version_id,
            channel=route.identity.channel,
            channel_user_id=route.identity.channel_user_id,
            language=language,
            last_message_at=now,
            created_at=now,
            updated_at=now,
        )
