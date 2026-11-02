"""
What a caller hears about the recording and the privacy notice, as
Settings → Calls shows it next to the recording switch: the sentence the
greeting uses for the business's country (where every party must consent,
or where the country is not known, the caller is told they may say no) and
where the privacy notice is, in each language of the business.
"""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import CountryRegistryContract
from app.schemas.constants.localization import RecordingConsentRule
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.calls.call_settings import CallNoticePreview
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import UnknownCountryError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.calls.call_privacy_texts import CALL_PRIVACY_NOTICE_HINT
from app.utilities.conversations.assistant_texts.call_consent_texts import (
    CALL_RECORDING_CONSENT,
)
from app.utilities.conversations.assistant_texts.call_texts import (
    CALL_RECORDING_NOTICE,
)
from app.utilities.scheduling.localized_formatting import choose_template_language


def recording_sentence(
    country_registry: CountryRegistryContract,
    business: BusinessDocument,
) -> LocalizedText:
    """
    The consent sentence where every party must agree (or where the
    country is not known), else the notice.
    """

    try:
        rule: RecordingConsentRule = country_registry.get(
            business.country_code
        ).recording_consent_rule
    except UnknownCountryError:
        return CALL_RECORDING_CONSENT

    if rule is RecordingConsentRule.ALL_PARTY_CONSENT:
        return CALL_RECORDING_CONSENT

    return CALL_RECORDING_NOTICE


def build_recording_notices(
    business: BusinessDocument,
    country_registry: CountryRegistryContract,
    text_resolver: LocalizedTextResolverContract,
) -> list[CallNoticePreview]:
    """The recording and privacy sentences in each language of the business."""

    sentence: LocalizedText = recording_sentence(country_registry, business)
    languages: list[LanguageTag] = []
    for language in [business.default_language, *business.languages]:
        text_language: LanguageTag = choose_template_language(sentence, language)
        if text_language not in languages:
            languages.append(text_language)

    return [
        CallNoticePreview(
            language=language,
            text=MessageText(
                f"{text_resolver.resolve(sentence, language)} "
                f"{text_resolver.resolve(CALL_PRIVACY_NOTICE_HINT, language)}"
            ),
        )
        for language in languages
    ]
