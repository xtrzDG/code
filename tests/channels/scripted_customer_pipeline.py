"""A stand-in for the conversation engine that answers channel messages by script."""

from typed_time_provider import Microseconds

from app.contracts.conversation_flow import CustomerMessagePipelineContract
from app.repositories.conversation_repositories import (
    ConversationRepository,
    MessageRepository,
)
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_fakes import AdjustableClock


class ScriptedCustomerPipeline(CustomerMessagePipelineContract):
    """
    Engine stand-in: answers "Reply: <text>", stays silent or fails. Like the
    engine it stores the conversation of each customer (the first one gets
    `conversation_id`) with the customer's message and the answer, under the
    ids the inbox chose. `interruptions` are raised one per turn before
    anything is stored (a worker killed mid-turn).
    """

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        clock: AdjustableClock,
    ) -> None:
        self.messages: list[InboundMessage] = []
        self.is_silent: bool = False
        self.failure: ApplicationError | None = None
        self.interruptions: list[BaseException] = []
        self.crashing_texts: set[str] = set()
        self.language: LanguageTag = LanguageTag("en")
        self.reply_text: str | None = None
        self.conversation_id: ConversationId = ConversationId()
        self._conversation_repo: ConversationRepository = conversation_repo
        self._message_repo: MessageRepository = message_repo
        self._clock: AdjustableClock = clock
        self._is_first_used: bool = False

    def start(self, input_data: InboundMessage) -> AssistantReply:
        self.messages.append(input_data)
        if self.interruptions:
            raise self.interruptions.pop(0)

        if self.failure is not None:
            raise self.failure

        if str(input_data.text) in self.crashing_texts:
            raise RuntimeError("a bug in a tool")

        text: MessageText | None = None
        if not self.is_silent:
            text = MessageText(self.reply_text or f"Reply: {input_data.text}")

        conversation: ConversationDocument = self._conversation_of(input_data)
        self._store(
            conversation,
            MessageAuthor.CUSTOMER,
            input_data.text,
            input_data.customer_message_id,
        )
        if text is not None:
            self._store(
                conversation, MessageAuthor.ASSISTANT, text, input_data.reply_message_id
            )

        return AssistantReply(
            conversation_id=conversation.id,
            text=text,
            language=self.language,
            is_handed_off=self.is_silent,
        )

    def _conversation_of(self, message: InboundMessage) -> ConversationDocument:
        now: Microseconds = self._clock.now_microseconds()
        status: ConversationStatus = (
            ConversationStatus.HANDOFF if self.is_silent else ConversationStatus.OPEN
        )
        for conversation in self._conversation_repo.list_by_business(
            message.business_id
        ):
            if (
                conversation.channel is message.channel
                and conversation.channel_user_id == message.channel_user_id
            ):
                conversation.status = status
                conversation.last_message_at = now
                self._conversation_repo.save(conversation)
                return conversation

        conversation = ConversationDocument(
            id=ConversationId() if self._is_first_used else self.conversation_id,
            business_id=message.business_id,
            contact_id=ContactId(),
            assistant_version_id=AssistantVersionId(),
            channel=message.channel,
            channel_user_id=message.channel_user_id,
            language=self.language,
            status=status,
            last_message_at=now,
            created_at=now,
            updated_at=now,
        )
        self._is_first_used = True
        self._conversation_repo.save(conversation)
        return conversation

    def _store(
        self,
        conversation: ConversationDocument,
        author: MessageAuthor,
        text: MessageText,
        message_id: MessageId | None,
    ) -> None:
        now: Microseconds = self._clock.now_microseconds()
        self._message_repo.save(
            MessageDocument(
                id=message_id or MessageId(),
                conversation_id=conversation.id,
                business_id=conversation.business_id,
                direction=(
                    MessageDirection.INBOUND
                    if author is MessageAuthor.CUSTOMER
                    else MessageDirection.OUTBOUND
                ),
                author=author,
                text=text,
                language=self.language,
                created_at=now,
                updated_at=now,
            )
        )
        # Each stored message gets its own instant, like real traffic.
        self._clock.advance_microseconds(1)
