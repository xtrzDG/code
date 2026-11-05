"""Where an owner picks a number at once, and where the team arranges it."""

import pytest

from app.registries.telephony.phone_number_countries import PHONE_NUMBER_COUNTRY_RULES
from app.registries.telephony.phone_number_country_registry import (
    PhoneNumberCountryRegistry,
)
from app.schemas.constants.phone_numbers import PhoneNumberAvailability, PhoneNumberType
from app.schemas.typings.localization.constrained_strings import CountryCode

REGISTRY = PhoneNumberCountryRegistry()


@pytest.mark.parametrize(
    ("country", "number_type", "expected"),
    [
        ("US", PhoneNumberType.LOCAL, PhoneNumberAvailability.SELF_SERVE),
        ("US", PhoneNumberType.TOLL_FREE, PhoneNumberAvailability.SELF_SERVE),
        ("CA", PhoneNumberType.LOCAL, PhoneNumberAvailability.SELF_SERVE),
        ("US", PhoneNumberType.MOBILE, PhoneNumberAvailability.REQUIRES_DOCUMENTS),
        ("GE", PhoneNumberType.LOCAL, PhoneNumberAvailability.REQUIRES_DOCUMENTS),
        ("DE", PhoneNumberType.TOLL_FREE, PhoneNumberAvailability.REQUIRES_DOCUMENTS),
        # Not listed: the team checks the country by hand.
        ("BR", PhoneNumberType.LOCAL, PhoneNumberAvailability.REQUIRES_DOCUMENTS),
    ],
)
def test_availability_by_country_and_kind(
    country: str, number_type: PhoneNumberType, expected: PhoneNumberAvailability
) -> None:
    assert REGISTRY.get_availability(CountryCode(country), number_type) is expected


def test_the_self_serve_countries_are_listed_in_order() -> None:
    assert [str(code) for code in REGISTRY.list_self_serve_countries()] == ["CA", "US"]


def test_every_listed_country_rules_every_kind() -> None:
    for country, kinds in PHONE_NUMBER_COUNTRY_RULES.items():
        assert set(kinds) == set(PhoneNumberType), country
        assert PhoneNumberAvailability.ON_REQUEST not in kinds.values(), country
