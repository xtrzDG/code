"""The sources report and the topics, wired over the value test world."""

from datetime import datetime

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.customer_source_repository import CustomerSourceRepository
from app.repositories.topic_repositories import (
    ConversationTopicsRepository,
    TopicInputRepository,
)
from app.schemas.constants.bookings import LeadType
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.conversation_topics import ConversationTopicsDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag
from app.use_cases.insights.topics.get_conversation_topics_use_case import (
    GetConversationTopicsUseCase,
)
from app.use_cases.insights.topics.group_conversation_topics_use_case import (
    GroupConversationTopicsUseCase,
)
from app.use_cases.insights.value.get_customer_sources_use_case import (
    GetCustomerSourcesUseCase,
)
from tests.value.value_scene import ValueScene, at


class InsightBench(ValueScene):
    """A value scene with sources on its conversations and a topics store."""

    def __init__(self, **options: object) -> None:
        super().__init__(**options)  # type: ignore[arg-type]
        self.topics_repo = ConversationTopicsRepository(
            InMemoryDocumentCollectionAdapter[ConversationTopicsDocument](
                ConversationTopicsDocument
            )
        )

    def tagged(
        self,
        local: str,
        source: str | None,
        channel: ChannelKind = ChannelKind.WHATSAPP,
        is_sandbox: bool = False,
        language: str | None = "ka",
    ) -> ConversationDocument:
        conversation = self.world.add_conversation(
            self.business,
            self.contact,
            channel,
            language=language,
            is_sandbox=is_sandbox,
            created_at=datetime.fromisoformat(local),
        )
        conversation.acquisition_source = (
            None if source is None else AcquisitionSourceTag(source)
        )
        self.world.conversation_repo.save(conversation)
        return conversation

    def request(self, local: str, conversation: ConversationDocument) -> None:
        moment = at(local)
        self.world.lead_repo.save(
            LeadDocument(
                business_id=self.business.id,
                contact_id=self.contact.id,
                conversation_id=conversation.id,
                lead_type=LeadType.BANQUET,
                details=LeadDetails("Birthday for 20"),
                source_channel=conversation.channel,
                created_at=moment,
                updated_at=moment,
            )
        )

    def says(self, conversation: ConversationDocument, local: str, text: str) -> None:
        moment = at(local)
        self.world.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=self.business.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=MessageText(text),
                created_at=moment,
                updated_at=moment,
            )
        )

    def sources(self) -> GetCustomerSourcesUseCase:
        return GetCustomerSourcesUseCase(
            authorize_business_access=self.world.authorize(),
            customer_source_repo=CustomerSourceRepository(
                self.world.conversation_collection,
                self.world.booking_collection,
                self.world.lead_collection,
            ),
            catalogs=self.world.catalogs(),
            wall_clock=self.world.clock.wall_clock,
        )

    def topics_job(self, llm: ScriptedLlmAdapter) -> GroupConversationTopicsUseCase:
        return GroupConversationTopicsUseCase(
            business_repo=self.world.business_repo,
            conversation_topics_repo=self.topics_repo,
            topic_input_repo=TopicInputRepository(
                self.world.conversation_collection, self.world.message_collection
            ),
            unanswered_question_repo=self.world.question_repo,
            llm_adapter=llm,
            app_settings=self.world.settings,
            wall_clock=self.world.clock.wall_clock,
        )

    def topics(self) -> GetConversationTopicsUseCase:
        return GetConversationTopicsUseCase(
            authorize_business_access=self.world.authorize(),
            conversation_topics_repo=self.topics_repo,
        )
