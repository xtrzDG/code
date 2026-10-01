from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import CountryRegistryContract
from app.contracts.repositories import BusinessProfileRepoContract, BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.localization import RecordingConsentRule
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.localization import CountryProfile
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    UnknownCountryError,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.assistant_texts import (
    CALL_GREETING,
    CALL_OPERATOR_HINT,
    CALL_RECORDING_NOTICE,
    fill_business_name,
)


class BuildCallGreetingUseCase(UseCaseContract[CallGreetingRequest, CallGreeting]):
    """
    First phrase of a phone call (concept section 7): who answers (the AI
    assistant of the business), that the call is recorded, and how to reach a
    human, in the requested language or the business greeting language.

    The recording sentence is said when the profile's recording notice is on
    (the default) or when the country requires the consent of every party,
    whatever the profile says.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        country_registry: CountryRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._country_registry: CountryRegistryContract = country_registry
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def run(self, input_data: CallGreetingRequest) -> CallGreeting:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        language: LanguageTag = (
            input_data.language
            if input_data.language is not None
            else business.default_language
        )
        sentences: list[str] = [
            fill_business_name(
                self._localized_text_resolver.resolve(CALL_GREETING, language),
                str(business.name),
            )
        ]
        if self._requires_recording_notice(business):
            sentences.append(
                self._localized_text_resolver.resolve(CALL_RECORDING_NOTICE, language)
            )

        sentences.append(
            self._localized_text_resolver.resolve(CALL_OPERATOR_HINT, language)
        )
        return CallGreeting(text=MessageText(" ".join(sentences)), language=language)

    def _requires_recording_notice(self, business: BusinessDocument) -> bool:
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        if profile is None or profile.is_recording_notice_enabled:
            return True

        try:
            country: CountryProfile = self._country_registry.get(business.country_code)
        except UnknownCountryError:
            return True

        return country.recording_consent_rule is RecordingConsentRule.ALL_PARTY_CONSENT
