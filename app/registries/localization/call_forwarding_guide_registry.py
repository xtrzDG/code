from app.contracts.catalog_registries import CallForwardingGuideRegistryContract
from app.registries.localization.call_forwarding_carriers import (
    CARRIER_GUIDES_BY_COUNTRY,
)
from app.registries.localization.call_forwarding_texts import (
    FORWARDING_NOTES,
    FORWARDING_STEPS,
    GSM_CODE_TEMPLATES,
)
from app.schemas.constants.localization import TextReviewStatus
from app.schemas.dto.catalog.call_forwarding import (
    CallForwardingGuide,
    CarrierForwardingGuide,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.utilities.localization.owner_texts import filled_owner_text

UNCONFIRMED_CARRIER_NOTE_KEY: str = "forwarding.carrier_unconfirmed"


class CallForwardingGuideRegistry(CallForwardingGuideRegistryContract):
    """
    Forwarding guides: GSM conditional-forwarding codes work in almost every
    mobile network, so every country gets them; countries with known carriers
    (Georgia, Armenia, Azerbaijan, Ukraine, Turkey, Germany, Israel) also
    list each carrier with what is known of it. A carrier whose codes are
    not yet checked against its own documentation (NEEDS_REVIEW) says so,
    so an owner whose code fails knows to ask the carrier.
    """

    def get(self, country_code: CountryCode) -> CallForwardingGuide:
        return CallForwardingGuide(
            country_code=country_code,
            code_templates=list(GSM_CODE_TEMPLATES),
            carriers=[
                with_review_note(carrier)
                for carrier in CARRIER_GUIDES_BY_COUNTRY.get(country_code, ())
            ],
            steps=list(FORWARDING_STEPS),
            notes=list(FORWARDING_NOTES),
        ).model_copy(deep=True)


def with_review_note(carrier: CarrierForwardingGuide) -> CarrierForwardingGuide:
    """The carrier's note, followed by "not yet confirmed" for a draft."""

    if carrier.review_status is TextReviewStatus.REVIEWED:
        return carrier

    unconfirmed: LocalizedText = filled_owner_text(
        UNCONFIRMED_CARRIER_NOTE_KEY, carrier=str(carrier.carrier_name)
    )
    if carrier.notes is None:
        return carrier.model_copy(update={"notes": unconfirmed})

    return carrier.model_copy(
        update={"notes": join_sentences(carrier.notes, unconfirmed)}
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
