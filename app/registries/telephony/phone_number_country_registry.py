from collections.abc import Mapping

from app.contracts.phone_numbers import PhoneNumberCountryRegistryContract
from app.registries.telephony.phone_number_countries import (
    PHONE_NUMBER_COUNTRY_RULES,
)
from app.schemas.constants.phone_numbers import PhoneNumberAvailability, PhoneNumberType
from app.schemas.typings.localization.constrained_strings import CountryCode


class PhoneNumberCountryRegistry(PhoneNumberCountryRegistryContract):
    """
    Where an owner can pick a number in the cabinet and have it at once
    (`phone_number_countries.py`); everywhere else the platform team
    arranges it from a request.
    """

    def __init__(
        self,
        rules: Mapping[
            CountryCode, Mapping[PhoneNumberType, PhoneNumberAvailability]
        ] = PHONE_NUMBER_COUNTRY_RULES,
    ) -> None:
        self._rules: Mapping[
            CountryCode, Mapping[PhoneNumberType, PhoneNumberAvailability]
        ] = rules

    def get_availability(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> PhoneNumberAvailability:
        return self._rules.get(country_code, {}).get(
            number_type, PhoneNumberAvailability.REQUIRES_DOCUMENTS
        )

    def list_self_serve_countries(self) -> list[CountryCode]:
        return sorted(
            (
                country_code
                for country_code, kinds in self._rules.items()
                if PhoneNumberAvailability.SELF_SERVE in kinds.values()
            ),
            key=str,
        )
