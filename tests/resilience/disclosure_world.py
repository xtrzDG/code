"""
One customer's first message whose turn is slow: the turn deadline's
"one moment" and the turn's own reply race to be the assistant's first
words. The real use cases over the channels testbed's repositories; a
message repository that can hold a chosen save at a gate lets a test stop
one side inside the reply's lock while the other one waits for it.
"""

import threading
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.reply_locks import ReplyLockRegistryContract
from app.repositories.conversation_repositories import MessageRepository
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversation_engine import TurnGate
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.dto.assistant_tools import AssistantToolContext
from app.schemas.dto.conversation_engine import PreparedTurn, ReplyRecord
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.use_cases.channels.inbox.send_holding_reply_use_case import (
    SendHoldingReplyUseCase,
)
from app.use_cases.conversations.record_assistant_reply_use_case import (
    RecordAssistantReplyUseCase,
)
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id
from tests.resilience.reply_speed_world import ReplySpeedTestbed

CUSTOMER: ChannelUserId = ChannelUserId("555000111")
ANSWER: MessageText = MessageText("We have a table at 8.")
WAIT_SECONDS: float = 10.0


class GatedMessages(MessageRepository):
    """Holds the save of one message id until the test opens the gate."""

    def __init__(self) -> None:
        super().__init__(InMemoryDocumentCollectionAdapter(MessageDocument))
        self.held_id: MessageId | None = None
        self.arrived: threading.Event = threading.Event()
        self.gate: threading.Event = threading.Event()

    def save(self, message: MessageDocument) -> None:
        if message.id == self.held_id:
            self.arrived.set()
            assert self.gate.wait(WAIT_SECONDS), "the test never opened the gate"
        super().save(message)


class WatchedLocks(ReplyLockRegistryContract):
    """The real reply locks, telling the test when a thread asks for one."""

    def __init__(self, inner: ReplyLockRegistryContract) -> None:
        self._inner: ReplyLockRegistryContract = inner
        self.asked: dict[str, threading.Event] = {}

    def waiting(self, thread_name: str) -> threading.Event:
        return self.asked.setdefault(thread_name, threading.Event())

    def lock_for_reply(
        self, business_id: BusinessId, reply_message_id: MessageId
    ) -> AbstractContextManager[object]:
        return self._held(business_id, reply_message_id)

    @contextmanager
    def _held(
        self, business_id: BusinessId, reply_message_id: MessageId
    ) -> Generator[object]:
        self.waiting(threading.current_thread().name).set()
        with self._inner.lock_for_reply(business_id, reply_message_id) as held:
            yield held


class DisclosureWorld:
    """A first customer message, its inbox event, its turn, both use cases."""

    def __init__(self) -> None:
        self.testbed = ReplySpeedTestbed()
        owner_id = self.testbed.add_user("owner")
        self.business = self.testbed.add_business(owner_id, name="Café Rustaveli")
        self.messages = GatedMessages()
        self.locks = WatchedLocks(self.testbed.reply_locks)
        self.version = self._version()
        self.contact = ContactDocument(business_id=self.business.id)
        self.conversation = ConversationDocument(
            business_id=self.business.id,
            contact_id=self.contact.id,
            assistant_version_id=self.version.id,
            channel=ChannelKind.TELEGRAM,
            channel_user_id=CUSTOMER,
            language=self.business.default_language,
            last_message_at=self.now(),
            created_at=self.now(),
            updated_at=self.now(),
        )
        self.testbed.conversation_repo.save(self.conversation)
        self.event = self._first_message()

    def holding(self) -> SendHoldingReplyUseCase:
        bed = self.testbed
        return SendHoldingReplyUseCase(
            bed.business_repo,
            self.messages,
            bed.conversation_repo,
            bed.outbound_message_repo,
            bed.job_queue,
            bed.text_resolver,
            bed.live_events,
            bed.wall_clock,
            self.locks,
        )

    def recorder(self) -> RecordAssistantReplyUseCase:
        bed = self.testbed
        return RecordAssistantReplyUseCase(
            message_repo=self.messages,
            conversation_repo=bed.conversation_repo,
            usage_event_repo=bed.usage_event_repo,
            localized_text_resolver=bed.text_resolver,
            live_events=bed.live_events,
            wall_clock=bed.wall_clock,
            reply_locks=self.locks,
        )

    def reply_record(self) -> ReplyRecord:
        return ReplyRecord(
            turn=self.turn(), text=ANSWER, model_id=self.version.model_id
        )

    def turn(self) -> PreparedTurn:
        language = self.business.default_language
        return PreparedTurn(
            business=self.business,
            version=self.version,
            contact=self.contact,
            conversation=self.conversation,
            reply_language=language,
            gate=TurnGate.ANSWER,
            is_new_conversation=True,
            is_first_reply=True,
            customer_text=MessageText("Do you have a table for 4 tonight?"),
            model_text=MessageText("Do you have a table for 4 tonight?"),
            reply_message_id=self.event.reply_message_id,
            context_line=MessageText("context"),
            tool_context=AssistantToolContext(
                business_id=self.business.id,
                business_country_code=self.business.country_code,
                contact_id=self.contact.id,
                conversation_id=self.conversation.id,
                channel=ChannelKind.TELEGRAM,
                language=language,
                available_tools=[],
            ),
            received_at=self.now(),
        )

    def assistant_texts(self) -> list[str]:
        return [
            str(message.text)
            for message in self.messages.list_by_business(self.business.id)
            if message.author is MessageAuthor.ASSISTANT
        ]

    def now(self) -> Microseconds:
        return self.testbed.clock.now_microseconds()

    def _version(self) -> AssistantVersionDocument:
        version = AssistantVersionDocument(
            business_id=self.business.id,
            version_number=AssistantVersionNumber(1),
            niche_key=NicheKey.RESTAURANT,
            model_id=LlmModelId("gpt-5-mini"),
            prompt_text=SystemPromptText("Prompt"),
            tools=[AssistantToolName.CREATE_BOOKING],
            languages=self.business.languages,
            default_language=self.business.default_language,
            is_voice_enabled=False,
            facts=[],
            profile_revision=Microseconds(1),
        )
        self.testbed.assistant_version_repo.save(version)
        return version

    def _first_message(self) -> InboundEventDocument:
        provider_message_id = ProviderMessageId("update_1")
        event = InboundEventDocument(
            id=derive_inbound_event_id(
                self.business.id, ChannelKind.TELEGRAM, provider_message_id
            ),
            business_id=self.business.id,
            kind=InboundEventKind.CUSTOMER_MESSAGE,
            channel=ChannelKind.TELEGRAM,
            provider_message_id=provider_message_id,
            customer_message=InboundCustomerMessage(
                channel_user_id=CUSTOMER,
                text=MessageText("Do you have a table for 4 tonight?"),
            ),
            created_at=self.now(),
            updated_at=self.now(),
        )
        self.messages.save(
            MessageDocument(
                id=event.customer_message_id,
                conversation_id=self.conversation.id,
                business_id=self.business.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=MessageText("Do you have a table for 4 tonight?"),
                channel=ChannelKind.TELEGRAM,
                created_at=self.now(),
                updated_at=self.now(),
            )
        )
        return event
