from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.channels.inbox.holding_outbox import queue_holding_reply
from app.utilities.channels.widget_live_signals import announce_widget_reply
from app.utilities.conversations.assistant_texts.ai_disclosure_texts import (
    AI_DISCLOSURE,
)
from app.utilities.conversations.assistant_texts.business_name_placeholder import (
    fill_business_name,
)
from app.utilities.conversations.assistant_texts.holding_texts import ONE_MOMENT
from app.utilities.deliveries.holding_replies import derive_holding_message_id

FALLBACK_LANGUAGE: LanguageTag = LanguageTag("en")
DISCLOSURE_SEPARATOR: str = "\n"


class SendHoldingReplyUseCase(UseCaseContract[InboundEventDocument, MessageId | None]):
    """
    The turn deadline passed and the reply is still being written: tell the
    customer, once, in their language, that the answer is coming
    (`ONE_MOMENT`, CHAT_TURN_DEADLINE_SECONDS after their first unanswered
    message). It goes through the outbox like every assistant reply
    (CUSTOMER_REPLY, one per reply: a turn that runs again never sends a
    second one) and into the transcript, where the website widget shows it.

    When it is the conversation's first assistant message, it opens with
    the AI disclosure: the customer learns they talk to an AI assistant
    with the first thing it says. Nothing is sent when the reply is already
    stored, the message is not in the conversation yet, or staff own the
    conversation (the assistant stays silent then). Returns the holding
    message's id when it was sent.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        message_repo: MessageRepoContract,
        conversation_repo: ConversationRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        localized_text_resolver: LocalizedTextResolverContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._message_repo: MessageRepoContract = message_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: InboundEventDocument) -> MessageId | None:
        event: InboundEventDocument = input_data
        if event.business_id is None or event.customer_message is None:
            return None

        holding_id: MessageId = derive_holding_message_id(event.reply_message_id)
        if (
            self._message_repo.get(event.business_id, event.reply_message_id)
            is not None
            or self._message_repo.get(event.business_id, holding_id) is not None
        ):
            return None

        customer_message: MessageDocument | None = self._message_repo.get(
            event.business_id, event.customer_message_id
        )
        conversation: ConversationDocument | None = (
            None
            if customer_message is None
            else self._conversation_repo.get(
                event.business_id, customer_message.conversation_id
            )
        )
        if (
            customer_message is None
            or conversation is None
            or conversation.status is ConversationStatus.HANDOFF
        ):
            return None

        language: LanguageTag = (
            customer_message.language or conversation.language or FALLBACK_LANGUAGE
        )
        text = MessageText(self._holding_text(conversation, language))
        now: Microseconds = self._wall_clock.now_unix()
        # The outbox first: a turn that dies after it finds the stored
        # message missing, queues nothing new and stores the message.
        queue_holding_reply(
            self._outbound_message_repo,
            self._job_queue,
            event,
            conversation.id,
            holding_id,
            text,
            now,
        )
        self._message_repo.save(
            MessageDocument(
                id=holding_id,
                conversation_id=conversation.id,
                business_id=event.business_id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.ASSISTANT,
                text=text,
                language=language,
                channel=conversation.channel,
                created_at=now,
                updated_at=now,
            )
        )
        self._live_events.publish(
            event.business_id,
            LiveEventKind.CONVERSATION_MESSAGE,
            (conversation.id,),
            is_sandbox=conversation.is_sandbox,
        )
        announce_widget_reply(self._live_events, conversation, holding_id)
        return holding_id

    def _holding_text(
        self, conversation: ConversationDocument, language: LanguageTag
    ) -> str:
        one_moment: str = self._localized_text_resolver.resolve(ONE_MOMENT, language)
        business: BusinessDocument | None = self._business_repo.get(
            conversation.business_id
        )
        if business is None or not self._is_first_reply(conversation):
            return one_moment

        disclosure: str = fill_business_name(
            self._localized_text_resolver.resolve(AI_DISCLOSURE, language),
            str(business.name),
        )
        return f"{disclosure}{DISCLOSURE_SEPARATOR}{one_moment}"

    def _is_first_reply(self, conversation: ConversationDocument) -> bool:
        return (
            conversation.channel is not ChannelKind.PHONE
            and int(
                self._message_repo.count_by_conversation(
                    conversation.business_id,
                    conversation.id,
                    MessageDirection.OUTBOUND,
                    author=MessageAuthor.ASSISTANT,
                )
            )
            == 0
        )
