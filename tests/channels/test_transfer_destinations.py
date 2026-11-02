"""Which staff numbers a call may be put through to (toll fraud guard)."""

import pytest

from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.utilities.channels.transfer_destinations import (
    COUNTRY_REASON,
    INVALID_NUMBER_REASON,
    NUMBER_TYPE_REASON,
    REFUSED_RANGE_REASON,
    find_transfer_refusal,
    is_transfer_destination_allowed,
)

ITALY: CountryCode = CountryCode("IT")


@pytest.mark.parametrize(
    "phone_number",
    [
        "+393471234567",  # an Italian mobile
        "+390612345678",  # a Rome landline
        "+33612345678",  # a French mobile (EU)
        "+4915112345678",  # a German mobile (EU)
    ],
)
def test_mobiles_and_landlines_of_the_country_and_the_eu_are_allowed(
    phone_number: str,
) -> None:
    assert is_transfer_destination_allowed(E164PhoneNumber(phone_number), ITALY)


@pytest.mark.parametrize(
    ("phone_number", "reason"),
    [
        # Italian special tariffs: premium (89x), 178, 199, 12xx.
        ("+39899123456", REFUSED_RANGE_REASON),
        ("+39892123", REFUSED_RANGE_REASON),
        ("+391781234567", REFUSED_RANGE_REASON),
        ("+39199123456", REFUSED_RANGE_REASON),
        ("+3912541234", REFUSED_RANGE_REASON),
        # Satellite and international networks.
        ("+8816212345678", REFUSED_RANGE_REASON),
        ("+870773123456", REFUSED_RANGE_REASON),
        ("+882161234567", REFUSED_RANGE_REASON),
        # Shared cost and toll-free numbers are no person's line.
        ("+39848123456", NUMBER_TYPE_REASON),
        ("+39800123456", NUMBER_TYPE_REASON),
        # Outside the business's country and the EU.
        ("+995555123456", COUNTRY_REASON),
        ("+12025550123", COUNTRY_REASON),
        ("+447911123456", COUNTRY_REASON),
        # Not a number of any plan.
        ("+3900000000", INVALID_NUMBER_REASON),
    ],
)
def test_premium_special_and_foreign_numbers_are_refused(
    phone_number: str, reason: str
) -> None:
    assert find_transfer_refusal(E164PhoneNumber(phone_number), ITALY) == reason


def test_the_business_s_own_country_is_allowed_outside_the_eu() -> None:
    assert is_transfer_destination_allowed(
        E164PhoneNumber("+995555123456"), CountryCode("GE")
    )
