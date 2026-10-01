from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.assistant_texts import (
    CALL_GREETING,
    CALL_OPERATOR_HINT,
    CALL_RECORDING_NOTICE,
    fill_business_name,
)
from app.utilities.localization.language_tags import base_language_code
from app.utilities.scheduling.localized_formatting import choose_template_language

ENGLISH_LANGUAGE_CODE: str = "en"


class BuildCallGreetingUseCase(UseCaseContract[CallGreetingRequest, CallGreeting]):
    """
    First phrase of a phone call (concept sections 6 and 7): who answers (the
    AI assistant of the business), that the call is recorded, and how to
    reach a human, in the requested language or the business greeting
    language.

    Every call is recorded (the voice platform keeps the audio and the
    transcript), so the recording sentence is always said: recording without
    telling the caller is not allowed in any country. The greeting reports
    the language it is actually written in: English when the requested
    language has no text, so the voice agent never labels English as
    another language.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def run(self, input_data: CallGreetingRequest) -> CallGreeting:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        requested_language: LanguageTag = (
            input_data.language
            if input_data.language is not None
            else business.default_language
        )
        language: LanguageTag = select_greeting_language(requested_language)
        sentences: list[str] = [
            fill_business_name(
                self._localized_text_resolver.resolve(CALL_GREETING, language),
                str(business.name),
            ),
            self._localized_text_resolver.resolve(CALL_RECORDING_NOTICE, language),
            self._localized_text_resolver.resolve(CALL_OPERATOR_HINT, language),
        ]
        return CallGreeting(text=MessageText(" ".join(sentences)), language=language)


def select_greeting_language(requested_language: LanguageTag) -> LanguageTag:
    """The requested tag when the greeting exists in its language, else English."""

    used_language: LanguageTag = choose_template_language(
        CALL_GREETING,
        requested_language,
    )
    if base_language_code(used_language) == base_language_code(requested_language):
        return requested_language

    return LanguageTag(ENGLISH_LANGUAGE_CODE)
