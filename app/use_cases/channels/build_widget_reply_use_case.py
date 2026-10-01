from app.contracts.registries import LanguageRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.localization import TextDirection
from app.schemas.dto.channels import WidgetReplyView
from app.schemas.dto.conversations import AssistantReply
from app.schemas.exceptions.application_errors import UnsupportedLanguageError


class BuildWidgetReplyUseCase(UseCaseContract[AssistantReply, WidgetReplyView]):
    """
    The assistant's answer as the website widget shows it, with the writing
    direction of the answer's language (left-to-right when unknown).
    """

    def __init__(self, language_registry: LanguageRegistryContract) -> None:
        self._language_registry: LanguageRegistryContract = language_registry

    def run(self, input_data: AssistantReply) -> WidgetReplyView:
        try:
            direction: TextDirection = self._language_registry.get(
                input_data.language
            ).direction
        except UnsupportedLanguageError:
            direction = TextDirection.LEFT_TO_RIGHT

        return WidgetReplyView(
            conversation_id=input_data.conversation_id,
            text=input_data.text,
            language=input_data.language,
            direction=direction,
            is_handed_off=input_data.is_handed_off,
        )
