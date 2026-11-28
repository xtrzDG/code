from app.contracts.catalog_registries import CallForwardingGuideRegistryContract
from app.registries.localization.call_forwarding_carriers import (
    CARRIER_GUIDES_BY_COUNTRY,
    COUNTRY_FORWARDING_TEXTS,
)
from app.registries.localization.call_forwarding_texts import (
    FORWARDING_NOTES,
    FORWARDING_STEPS,
    GSM_CODE_TEMPLATES,
    UNCONFIRMED_CARRIER_CODES_NOTE,
)
from app.schemas.constants.localization import TextReviewStatus
from app.schemas.dto.catalog.call_forwarding import (
    CallForwardingGuide,
    CarrierForwardingGuide,
    CountryForwardingTexts,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCodeTemplate,
    CountryCode,
)
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.utilities.localization.owner_texts import filled_owner_text

UNCONFIRMED_CARRIER_NOTE_KEY: str = "forwarding.carrier_unconfirmed"
STANDARD_FORWARDING_TEXTS: CountryForwardingTexts = CountryForwardingTexts(
    code_templates=list(GSM_CODE_TEMPLATES),
    steps=list(FORWARDING_STEPS),
    notes=list(FORWARDING_NOTES),
)
STANDARD_DIAL_CODE_TEMPLATES: tuple[CallForwardingDialCodeTemplate, ...] = tuple(
    template.dial_code_template for template in GSM_CODE_TEMPLATES
)


class CallForwardingGuideRegistry(CallForwardingGuideRegistryContract):
    """
    Forwarding guides: GSM conditional-forwarding codes work in almost every
    mobile network, so every country gets them; countries with known carriers
    (Georgia, Armenia, Azerbaijan, Ukraine, Turkey, Italy, Germany, Israel)
    also list each carrier with what is known of it. In a country whose
    carriers take different codes (the United States) the owner opens their
    carrier first: it has its own steps, notes and top-level codes, the
    standard ones for carriers not listed. A carrier whose codes are not yet
    checked against its own documentation (NEEDS_REVIEW) says so, so an
    owner whose code fails knows to ask the carrier.
    """

    def get(self, country_code: CountryCode) -> CallForwardingGuide:
        texts: CountryForwardingTexts = COUNTRY_FORWARDING_TEXTS.get(
            country_code, STANDARD_FORWARDING_TEXTS
        )
        return CallForwardingGuide(
            country_code=country_code,
            code_templates=list(texts.code_templates),
            carriers=[
                with_review_note(carrier)
                for carrier in CARRIER_GUIDES_BY_COUNTRY.get(country_code, ())
            ],
            steps=list(texts.steps),
            notes=list(texts.notes),
            is_carrier_choice_needed=texts.is_carrier_choice_needed,
        ).model_copy(deep=True)


def with_review_note(carrier: CarrierForwardingGuide) -> CarrierForwardingGuide:
    """
    The carrier's note, followed by "not yet confirmed" for a draft: "Standard
    GSM codes, not yet confirmed with <carrier>" for the standard codes, the
    unconfirmed note of a carrier's own codes (a star code, another cancel
    code) otherwise.
    """

    if carrier.review_status is TextReviewStatus.REVIEWED:
        return carrier

    unconfirmed: LocalizedText = (
        filled_owner_text(
            UNCONFIRMED_CARRIER_NOTE_KEY, carrier=str(carrier.carrier_name)
        )
        if has_standard_codes(carrier)
        else UNCONFIRMED_CARRIER_CODES_NOTE
    )
    if carrier.notes is None:
        return carrier.model_copy(update={"notes": unconfirmed})

    return carrier.model_copy(
        update={"notes": join_sentences(carrier.notes, unconfirmed)}
    )


def has_standard_codes(carrier: CarrierForwardingGuide) -> bool:
    """The standard GSM codes and nothing else, in any number format."""

    return carrier.star_code_templates == [] and (
        tuple(template.dial_code_template for template in carrier.code_templates)
        == STANDARD_DIAL_CODE_TEMPLATES
    )


def join_sentences(first: LocalizedText, second: LocalizedText) -> LocalizedText:
    """Both texts in each language that has both, the second after a space."""

    return LocalizedText(
        values={
            language: LocalizedTextValue(f"{value} {second.values[language]}")
            for language, value in first.values.items()
            if language in second.values
        }
    )
