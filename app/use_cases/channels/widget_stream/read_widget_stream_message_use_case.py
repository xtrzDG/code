from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.constants.localization import TextDirection
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels.widget_streams import (
    WidgetStreamMessageQuery,
    WidgetStreamMessageView,
)
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.utilities.channels.widget_visitors import widget_visitor_id

# Messages a widget shows besides the visitor's own (as its polls).
SHOWN_AUTHORS: frozenset[MessageAuthor] = frozenset(
    {MessageAuthor.ASSISTANT, MessageAuthor.STAFF, MessageAuthor.SYSTEM}
)


class ReadWidgetStreamMessageUseCase(
    UseCaseContract[WidgetStreamMessageQuery, WidgetStreamMessageView | None]
):
    """
    The message a `widget.reply` event names, as the visitor's stream tells
    it: only when it is the visitor's own (a message to them in a website
    chat conversation of theirs), else nothing. Its text goes with it only
    when the model wrote it and the reply guard passed it as CLEAN; any
    other text (staff's, the platform's, a rewritten or held reply) the
    widget fetches with its next poll, which also replaces a draft with
    the stored text.
    """

    def __init__(
        self,
        message_repo: MessageRepoContract,
        conversation_repo: ConversationRepoContract,
        language_registry: LanguageRegistryContract,
    ) -> None:
        self._message_repo: MessageRepoContract = message_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._language_registry: LanguageRegistryContract = language_registry

    def run(
        self, input_data: WidgetStreamMessageQuery
    ) -> WidgetStreamMessageView | None:
        message: MessageDocument | None = self._message_repo.get(
            input_data.business_id, input_data.message_id
        )
        if (
            message is None
            or message.direction is not MessageDirection.OUTBOUND
            or message.author not in SHOWN_AUTHORS
        ):
            return None

        conversation: ConversationDocument | None = self._conversation_repo.get(
            input_data.business_id, message.conversation_id
        )
        if (
            conversation is None
            or conversation.channel is not ChannelKind.WEB_CHAT
            or widget_visitor_id(str(conversation.channel_user_id))
            != input_data.visitor_id
        ):
            return None

        return WidgetStreamMessageView(
            message_id=message.id,
            author=message.author,
            text=message.text if is_cleared_draft(message) else None,
            direction=self._direction(message),
        )

    def _direction(self, message: MessageDocument) -> TextDirection:
        if message.language is None:
            return TextDirection.LEFT_TO_RIGHT

        try:
            return self._language_registry.get(message.language).direction
        except UnsupportedLanguageError:
            return TextDirection.LEFT_TO_RIGHT


def is_cleared_draft(message: MessageDocument) -> bool:
    """A model reply the guard passed as it was: safe to show at once."""

    return (
        message.author is MessageAuthor.ASSISTANT
        and message.model_id is not None
        and message.guard_verdict is ReplyGuardVerdict.CLEAN
    )
