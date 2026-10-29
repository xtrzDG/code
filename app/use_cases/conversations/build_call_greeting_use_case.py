from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import CountryRegistryContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.localization import RecordingConsentRule
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    UnknownCountryError,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
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
    CALL_RECORDING_NOTICE,
)
from app.utilities.localization.language_tags import base_language_code
from app.utilities.scheduling.localized_formatting import choose_template_language

ENGLISH_LANGUAGE_CODE: str = "en"


class BuildCallGreetingUseCase(UseCaseContract[CallGreetingRequest, CallGreeting]):
    """
    First phrase of a phone call (concept sections 6 and 7): who answers (the
    AI assistant of the business), which other languages the business
    speaks (the caller may answer in any of them; the voice agent follows),
    that the call is recorded, and how to reach a human, in the requested
    language or the business greeting language.

    Every call is recorded (the voice platform keeps the audio and the
    transcript), so the recording sentence is always said: recording without
    telling the caller is not allowed in any country. Where the business's
    country asks every party's consent (`RecordingConsentRule`), the
    sentence also tells the caller they may say no and go on without a
    recording (CALL_RECORDING_CONSENT; the agent then calls
    decline_recording). The greeting reports the language it is actually
    written in: English when the requested language has no text, so the
    voice agent never labels English as another language.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
        country_registry: CountryRegistryContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._country_registry: CountryRegistryContract = country_registry

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
        sentences: list[str] = [
            fill_business_name(
                self._localized_text_resolver.resolve(CALL_GREETING, language),
                str(business.name),
            ),
            *([offer] if offer is not None else []),
            self._localized_text_resolver.resolve(
                self._recording_sentence(business), language
            ),
            self._localized_text_resolver.resolve(CALL_OPERATOR_HINT, language),
        ]
        return CallGreeting(text=MessageText(" ".join(sentences)), language=language)

    def _recording_sentence(self, business: BusinessDocument) -> LocalizedText:
        """
        The consent sentence where every party must agree (or where the
        country is not known, the careful choice), else the notice.
        """

        try:
            rule: RecordingConsentRule = self._country_registry.get(
                business.country_code
            ).recording_consent_rule
        except UnknownCountryError:
            return CALL_RECORDING_CONSENT

        if rule is RecordingConsentRule.ALL_PARTY_CONSENT:
            return CALL_RECORDING_CONSENT

        return CALL_RECORDING_NOTICE


def select_greeting_language(requested_language: LanguageTag) -> LanguageTag:
    """The requested tag when the greeting exists in its language, else English."""

    used_language: LanguageTag = choose_template_language(
        CALL_GREETING,
        requested_language,
    )
    if base_language_code(used_language) == base_language_code(requested_language):
        return requested_language

    return LanguageTag(ENGLISH_LANGUAGE_CODE)
