"""
Which staff numbers a call may be put through to (a transfer of the voice
agent, or the fallback dial when the voice platform did not take a call).

Every transfer is an outgoing leg the platform pays for, and a number the
owner saves is reachable by whoever gets the cabinet's settings: a premium
or shared-cost line there would turn every call into toll fraud
(international revenue share fraud). So a destination must be an
ordinary mobile or landline of the business's own country or of an EU
member state, as the numbering plans describe it, and never one of the
special-tariff ranges below, which stay refused even if a numbering plan
ever marks them otherwise. The rule is checked when the staff number is
saved and again right before every dial.
"""

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumber, PhoneNumberType

from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    PhoneNumberPrefix,
)

# The EU member states: a staff mobile abroad (a seasonal manager on a
# Romanian number) is fine there, any other country is not.
EU_COUNTRY_CODES: frozenset[CountryCode] = frozenset(
    CountryCode(code)
    for code in (
        "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR",
        "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI",
        "SK",
    )
)  # fmt: skip
# Only people answer a transfer: mobiles and landlines.
TRANSFERABLE_NUMBER_TYPES: frozenset[int] = frozenset(
    {
        PhoneNumberType.MOBILE,
        PhoneNumberType.FIXED_LINE,
        PhoneNumberType.FIXED_LINE_OR_MOBILE,
    }
)
REFUSED_TRANSFER_PREFIXES: tuple[PhoneNumberPrefix, ...] = (
    # Italy: premium-rate services (89x), special and premium numbers
    # (178), personal and shared-cost numbers (199), directory and
    # information services (12xx), old premium ranges (144, 166).
    PhoneNumberPrefix("+3989"),
    PhoneNumberPrefix("+39178"),
    PhoneNumberPrefix("+39199"),
    PhoneNumberPrefix("+3912"),
    PhoneNumberPrefix("+39144"),
    PhoneNumberPrefix("+39166"),
    # Inmarsat, the global mobile satellite systems (Iridium, Thuraya,
    # Globalstar) and the international networks: classic IRSF targets.
    PhoneNumberPrefix("+870"),
    PhoneNumberPrefix("+881"),
    PhoneNumberPrefix("+882"),
    PhoneNumberPrefix("+883"),
    # The international premium rate service.
    PhoneNumberPrefix("+979"),
)
REFUSED_RANGE_REASON: str = (
    "This number is in a premium, special-tariff or satellite range; calls "
    "are never put through to it."
)
INVALID_NUMBER_REASON: str = "This is not a valid phone number."
NUMBER_TYPE_REASON: str = (
    "Calls are put through only to an ordinary mobile or landline number, "
    "never to a premium, shared-cost, toll-free or personal number."
)
COUNTRY_REASON: str = (
    "Calls are put through only to numbers of the business's country or of "
    "an EU member state."
)


def find_transfer_refusal(
    phone_number: E164PhoneNumber,
    business_country_code: CountryCode,
) -> str | None:
    """
    Why a call must not be put through to the number (in English, for the
    owner's form and the logs), or None when it may.
    """

    if str(phone_number).startswith(
        tuple(str(prefix) for prefix in REFUSED_TRANSFER_PREFIXES)
    ):
        return REFUSED_RANGE_REASON

    try:
        parsed: PhoneNumber = phonenumbers.parse(str(phone_number))
    except NumberParseException:
        return INVALID_NUMBER_REASON

    if not phonenumbers.is_valid_number(parsed):
        return INVALID_NUMBER_REASON

    if phonenumbers.number_type(parsed) not in TRANSFERABLE_NUMBER_TYPES:
        return NUMBER_TYPE_REASON

    region: str | None = phonenumbers.region_code_for_number(parsed)
    if region != str(business_country_code) and region not in EU_COUNTRY_CODES:
        return COUNTRY_REASON

    return None


def is_transfer_destination_allowed(
    phone_number: E164PhoneNumber,
    business_country_code: CountryCode,
) -> bool:
    """A call may be put through to the number (`find_transfer_refusal`)."""

    return find_transfer_refusal(phone_number, business_country_code) is None
