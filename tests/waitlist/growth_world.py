"""
The operations world with what the waitlist and the campaigns add: a live
Tbilisi restaurant with Telegram connected, guests reachable there, the
outbox, the suppression list and the proactive routing and sending.
"""

from datetime import datetime

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import ChannelRepository
from app.repositories.delivery_repositories import OutboundMessageRepository
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.shared.proactive_letters import ProactiveSender
from app.use_cases.shared.proactive_routes import ProactiveRouting
from tests.operations.builders import DEFAULT_NOW
from tests.operations.operations_world import OperationsWorld
from tests.privacy.suppression_doubles import build_suppression_list


class GrowthWorld(OperationsWorld):
    """A live restaurant (Table 4, Table 8) whose guests write in Telegram."""

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        super().__init__(now)
        self.channel_repo = ChannelRepository(self.channel_collection)
        self.outbox_collection = InMemoryDocumentCollectionAdapter(
            OutboundMessageDocument
        )
        self.outbox = OutboundMessageRepository(self.outbox_collection)
        self.suppression_list = build_suppression_list()
        self.routing = ProactiveRouting(
            channel_repo=self.channel_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
        )
        self.sender = ProactiveSender(
            outbound_message_repo=self.outbox,
            job_queue=self.job_queue,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            unit_of_work=None,
        )
        self.business: BusinessDocument = self.add_business(name="Salobie Bia")
        self.business.status = BusinessStatus.LIVE
        self.business_repo.save(self.business)
        self.add_profile(self.business, min_notice_minutes=60)
        self.table_for_four: ResourceDocument = self.add_resource(
            self.business, "Table 4", capacity=4
        )
        self.table_for_eight: ResourceDocument = self.add_resource(
            self.business, "Table 8", capacity=8
        )
        self.telegram: ChannelDocument = ChannelDocument(
            business_id=self.business.id,
            kind=ChannelKind.TELEGRAM,
            external_id=ChannelExternalId("restaurant_bot"),
            status=ChannelStatus.CONNECTED,
        )
        self.channel_repo.save(self.telegram)
        self._next_account: int = 700_000

    def guest(
        self, name: str, language: str = "ru", phone: str | None = None
    ) -> ContactDocument:
        """A guest known in Telegram, in their own conversation there."""

        self._next_account += 1
        contact = self.add_contact(self.business, name, phone, language)
        contact.channel_identities = [
            ChannelIdentity(
                channel=ChannelKind.TELEGRAM,
                channel_user_id=ChannelUserId(str(self._next_account)),
            )
        ]
        self.contact_repo.save(contact)
        return contact

    def telegram_conversation(self, contact: ContactDocument) -> ConversationDocument:
        conversation = self.add_conversation(
            self.business, contact, channel=ChannelKind.TELEGRAM
        )
        identity = contact.channel_identities[0]
        conversation.channel_user_id = identity.channel_user_id
        conversation.language = contact.language or LanguageTag("ru")
        self.conversation_repo.save(conversation)
        return conversation

    def outbox_messages(self) -> list[OutboundMessageDocument]:
        """The messages queued in the outbox, oldest first."""

        return sorted(
            self.outbox_collection.list_all(),
            key=lambda message: (int(message.created_at), str(message.id)),
        )

    def outbox_texts(self) -> list[str]:
        return [str(message.text) for message in self.outbox_messages()]

    def renamed(self, contact: ContactDocument, name: str) -> ContactDocument:
        contact.name = ContactName(name)
        self.contact_repo.save(contact)
        return contact
