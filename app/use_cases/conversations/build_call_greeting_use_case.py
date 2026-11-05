from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.calls.call_privacy_texts import CALL_PRIVACY_NOTICE_HINT
from app.utilities.conversations.assistant_texts.business_name_placeholder import (
    fill_business_name,
)
from app.utilities.conversations.assistant_texts.call_consent_texts import (
    CALL_RECORDING_CONSENT,
)
from app.utilities.conversations.assistant_texts.call_language_offer import (
    language_offer_sentence,
    other_languages,
)
from app.utilities.conversations.assistant_texts.call_texts import (
    CALL_GREETING,
    CALL_OPERATOR_HINT,
)
from app.utilities.localization.language_tags import base_language_code
from app.utilities.scheduling.localized_formatting import choose_template_language

ENGLISH_LANGUAGE_CODE: str = "en"


class BuildCallGreetingUseCase(UseCaseContract[CallGreetingRequest, CallGreeting]):
    """
    First phrase of a phone call (concept sections 6 and 7): who answers (the
    AI assistant of the business), which other languages the business
    speaks (the caller may answer in any of them; the voice agent follows),
    that the call is recorded when the business records calls, how to reach
    a human and where the privacy notice is, in the requested language or
    the business greeting language.

    Recording is off unless the owner switched it on (call settings): then
    the recording sentence is said, since recording without telling the
    caller is not allowed in any country, and in every country it tells
    the caller they may say no and go on without a recording
    (CALL_RECORDING_CONSENT; the agent then calls decline_recording): where
    the law asks every party's consent as the consent, elsewhere as the
    non-recorded path the GDPR asks for when a recording is not necessary.
    With recording off nothing is said about a recording. Every greeting
    ends with the first layer of the privacy notice
    (CALL_PRIVACY_NOTICE_HINT: the business as the one responsible for the
    data, the purpose, where the full notice is), once: the agent's default
    first message and each call's greeting alike. The
    greeting reports the language it is actually written in: English when
    the requested language has no text, so the voice agent never labels
    English as another language.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
        call_settings_repo: CallSettingsRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._call_settings_repo: CallSettingsRepoContract = call_settings_repo
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
        offer: str | None = language_offer_sentence(
            language, other_languages(business.languages, language)
        )
        recording: LocalizedText | None = self._recording_sentence(business)
        sentences: list[str] = [
            fill_business_name(
                self._localized_text_resolver.resolve(CALL_GREETING, language),
                str(business.name),
            ),
            *([offer] if offer is not None else []),
            *(
                []
                if recording is None
                else [self._localized_text_resolver.resolve(recording, language)]
            ),
            self._localized_text_resolver.resolve(CALL_OPERATOR_HINT, language),
            fill_business_name(
                self._localized_text_resolver.resolve(
                    CALL_PRIVACY_NOTICE_HINT, language
                ),
                str(business.name),
            ),
        ]
        return CallGreeting(text=MessageText(" ".join(sentences)), language=language)

    def _recording_sentence(self, business: BusinessDocument) -> LocalizedText | None:
        """
        None while the business does not record calls (the default); else
        the sentence that the call is recorded and the caller may go on
        without a recording.
        """

        settings: CallSettingsDocument | None = (
            self._call_settings_repo.get_by_business(business.id)
        )
        if settings is None or not settings.is_recording_enabled:
            return None

        return CALL_RECORDING_CONSENT


def select_greeting_language(requested_language: LanguageTag) -> LanguageTag:
    """The requested tag when the greeting exists in its language, else English."""

    used_language: LanguageTag = choose_template_language(
        CALL_GREETING,
        requested_language,
    )
    if base_language_code(used_language) == base_language_code(requested_language):
        return requested_language

    return LanguageTag(ENGLISH_LANGUAGE_CODE)
