from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.localization import TextDirection
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels.widget_handoff import (
    WidgetHandoffNotice,
    WidgetHandoffView,
)
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.conversations.prefixed_id import MessageId


class RecordWidgetHandoffNoticeUseCase(
    UseCaseContract[WidgetHandoffNotice, WidgetHandoffView]
):
    """
    Keep what the visitor was told after "Talk to a person" in the
    conversation (an assistant message, so staff see the promise and the
    widget's polling finds it), and answer the widget with it and the
    direction of its language. Without a text (staff already had the
    conversation) nothing is stored.
    """

    def __init__(
        self,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        language_registry: LanguageRegistryContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WidgetHandoffNotice) -> WidgetHandoffView:
        message_id: MessageId | None = None
        if input_data.text is not None:
            message_id = self._store(input_data)

        return WidgetHandoffView(
            conversation_id=input_data.conversation_id,
            is_handed_off=True,
            message_id=message_id,
            text=input_data.text,
            language=input_data.language,
            direction=self._direction(input_data),
        )

    def _store(self, notice: WidgetHandoffNotice) -> MessageId | None:
        conversation: ConversationDocument | None = self._conversation_repo.get(
            notice.business_id, notice.conversation_id
        )
        if conversation is None or notice.text is None:
            return None

        now: Microseconds = self._wall_clock.now_unix()
        message = MessageDocument(
            conversation_id=conversation.id,
            business_id=conversation.business_id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.ASSISTANT,
            text=notice.text,
            language=notice.language,
            created_at=now,
            updated_at=now,
        )
        self._message_repo.save(message)
        conversation.last_message_at = now
        conversation.updated_at = now
        self._conversation_repo.save(conversation)
        self._live_events.publish(
            conversation.business_id,
            LiveEventKind.CONVERSATION_MESSAGE,
            (conversation.id,),
            is_sandbox=conversation.is_sandbox,
        )
        return message.id

    def _direction(self, notice: WidgetHandoffNotice) -> TextDirection:
        try:
            return self._language_registry.get(notice.language).direction
        except UnsupportedLanguageError:
            return TextDirection.LEFT_TO_RIGHT
