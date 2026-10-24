"""
Sending a request for feedback: the text in the customer's language, the
outbox message that carries it (free text, or the WhatsApp template with
the business name as its parameter), and the conversation that shows it,
where the customer's rating then lands.
"""

from dataclasses import dataclass
from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
    OutboundTemplate,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_strings import OutboundRecipientKey
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.feedback.request.feedback_routes import FeedbackRoute
from app.utilities.channels.language_codes import to_whatsapp_template_language
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    encode_outbound_message_payload,
)
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
    outbound_serial_key,
)
from app.utilities.feedback.feedback_keys import feedback_idempotency_key
from app.utilities.feedback.feedback_request_texts import FEEDBACK_REQUEST_TEXT

MICROSECONDS_PER_SECOND: int = 1_000_000
# A customer message within a day joins the conversation it continues.
CONVERSATION_WINDOW: timedelta = timedelta(hours=24)


def feedback_message_id(request: FeedbackRequestDocument) -> OutboundMessageId:
    """The outbox message of a request (derived: queued once)."""

    return derive_outbound_message_id(
        request.business_id, feedback_idempotency_key(request.id)
    )


@dataclass(frozen=True)
class FeedbackSender:
    outbound_message_repo: OutboundMessageRepoContract
    job_queue: JobQueueFacilitatorContract
    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    text_resolver: LocalizedTextResolverContract

    def request_text(
        self, business: BusinessDocument, language: LanguageTag
    ) -> MessageText:
        template: str = str(self.text_resolver.resolve(FEEDBACK_REQUEST_TEXT, language))
        return MessageText(template.format(business=business.name))

    def queue(
        self,
        business: BusinessDocument,
        request: FeedbackRequestDocument,
        route: FeedbackRoute,
        text: MessageText,
        now: Microseconds,
    ) -> None:
        """The outbox message and its delivery job (once per request)."""

        recipient_key: OutboundRecipientKey = customer_recipient_key(
            route.channel.id, route.identity.channel_user_id
        )
        template: OutboundTemplate | None = (
            None
            if route.template_name is None
            else OutboundTemplate(
                name=route.template_name,
                language_code=to_whatsapp_template_language(request.language),
                body_parameters=[MessageText(str(business.name))],
            )
        )
        message = OutboundMessageDocument(
            id=feedback_message_id(request),
            business_id=business.id,
            kind=OutboundMessageKind.CUSTOMER_REPLY,
            idempotency_key=feedback_idempotency_key(request.id),
            recipient_key=recipient_key,
            customer=CustomerRecipient(
                channel_id=route.channel.id,
                channel=route.identity.channel,
                channel_user_id=route.identity.channel_user_id,
            ),
            text=text,
            template=template,
            feedback_request_id=request.id,
            created_at=now,
            updated_at=now,
        )
        if not self.outbound_message_repo.insert_if_new(message):
            return

        self.job_queue.enqueue(
            DELIVER_OUTBOUND_JOB,
            encode_outbound_message_payload(message.id),
            business.id,
            lane=JobLane.OUTBOUND,
            serial_key=outbound_serial_key(business.id, recipient_key),
        )

    def show_in_conversation(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        route: FeedbackRoute,
        text: MessageText,
        language: LanguageTag,
        now: Microseconds,
    ) -> ConversationId | None:
        """
        The request as the newest message of the customer's conversation in
        that messenger (an open one of the last day, else a new one pinned
        to the live version; None while the business has none), written by
        the business, so staff and the assistant see what was asked.
        """

        conversation: ConversationDocument | None = self._open_conversation(
            business, contact, route, language, now
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
                text=text,
                language=language,
                created_at=now,
                updated_at=now,
            )
        )
        return conversation.id

    def _open_conversation(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        route: FeedbackRoute,
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
