from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.localization import TextDirection
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.channels.widget import WidgetReplyInput, WidgetReplyView
from app.schemas.dto.conversations import AssistantReply
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.conversations.prefixed_id import MessageId


class BuildWidgetReplyUseCase(UseCaseContract[WidgetReplyInput, WidgetReplyView]):
    """
    The assistant's answer as the website widget shows it, with the writing
    direction of the answer's language (left-to-right when unknown), the
    stored answer's id and the polling position: the visitor's message the
    answer replies to, so staff messages written meanwhile are not missed.
    """

    def __init__(
        self,
        message_repo: MessageRepoContract,
        language_registry: LanguageRegistryContract,
    ) -> None:
        self._message_repo: MessageRepoContract = message_repo
        self._language_registry: LanguageRegistryContract = language_registry

    def run(self, input_data: WidgetReplyInput) -> WidgetReplyView:
        reply: AssistantReply = input_data.reply
        try:
            direction: TextDirection = self._language_registry.get(
                reply.language
            ).direction
        except UnsupportedLanguageError:
            direction = TextDirection.LEFT_TO_RIGHT

        message_id, cursor = self._locate(input_data)
        return WidgetReplyView(
            conversation_id=reply.conversation_id,
            text=reply.text,
            language=reply.language,
            direction=direction,
            is_handed_off=reply.is_handed_off,
            message_id=message_id,
            cursor=cursor,
        )

    def _locate(
        self,
        input_data: WidgetReplyInput,
    ) -> tuple[MessageId | None, MessageId | None]:
        """The stored answer and the visitor message just before it."""

        messages: list[MessageDocument] = self._message_repo.list_by_conversation(
            input_data.business_id, input_data.reply.conversation_id
        )
        answer_index: int | None = None
        if input_data.reply.text is not None:
            for index in range(len(messages) - 1, -1, -1):
                message: MessageDocument = messages[index]
                if (
                    message.author is MessageAuthor.ASSISTANT
                    and message.text == input_data.reply.text
                ):
                    answer_index = index
                    break

        end: int = len(messages) if answer_index is None else answer_index
        cursor: MessageId | None = None
        for index in range(end - 1, -1, -1):
            if messages[index].author is MessageAuthor.CUSTOMER:
                cursor = messages[index].id
                break

        return (
            None if answer_index is None else messages[answer_index].id,
            cursor,
        )
