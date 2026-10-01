from app.contracts.catalog_registries import CallForwardingGuideRegistryContract
from app.registries.localization.call_forwarding_texts import (
    CARRIER_GUIDES_BY_COUNTRY,
    FORWARDING_NOTES,
    FORWARDING_STEPS,
    GSM_CODE_TEMPLATES,
)
from app.schemas.dto.catalog import CallForwardingGuide
from app.schemas.typings.localization.constrained_strings import CountryCode


class CallForwardingGuideRegistry(CallForwardingGuideRegistryContract):
    """
    Forwarding guides: GSM conditional-forwarding codes work in almost every
    mobile network, so every country gets them; countries with known carriers
    (Georgia: Magti, Silknet, Cellfie) also list each carrier with its notes.
    """

    def get(self, country_code: CountryCode) -> CallForwardingGuide:
        return CallForwardingGuide(
            country_code=country_code,
            code_templates=list(GSM_CODE_TEMPLATES),
            carriers=list(CARRIER_GUIDES_BY_COUNTRY.get(country_code, ())),
            steps=list(FORWARDING_STEPS),
            notes=list(FORWARDING_NOTES),
        ).model_copy(deep=True)
