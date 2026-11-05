"""Phone numbers that messaging platforms report, read into E.164.

WhatsApp ids and Telegram shared contacts carry international numbers,
usually as bare digits. Two WhatsApp quirks are known: Brazilian mobile ids
may lack the ninth digit ("55 11 8765-4321" for +55 11 98765-4321) and
Mexican ids keep the old mobile "1" after +52.
"""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput

PLUS_SIGN: str = "+"
BRAZIL_CALLING_CODE: str = "55"
BRAZIL_ID_WITHOUT_NINTH_DIGIT_LENGTH: int = 12
BRAZIL_OLD_MOBILE_FIRST_DIGITS: frozenset[str] = frozenset({"6", "7", "8", "9"})
MEXICO_OLD_MOBILE_PREFIX: str = "521"
MEXICO_ID_WITH_OLD_PREFIX_LENGTH: int = 13
MAX_PHONE_INPUT_LENGTH: int = 32


def to_international_input(raw_number: str) -> RawPhoneNumberInput:
    """Prefix "+" to a number given as international digits only."""

    trimmed: str = raw_number.strip()
    if trimmed.isascii() and trimmed.isdigit():
        return RawPhoneNumberInput(PLUS_SIGN + trimmed)

    return RawPhoneNumberInput(trimmed)


def parse_messaging_phone_number(
    phone_number_parser: PhoneNumberParserContract,
    raw_number: str,
    country_hint: CountryCode | None = None,
) -> E164PhoneNumber | None:
    """
    The E.164 form of a number a platform reported, or None when it is not
    a valid number of any country (the message is still answered).
    """

    if raw_number.strip() == "" or len(raw_number) > MAX_PHONE_INPUT_LENGTH:
        return None

    for candidate in list_candidate_inputs(raw_number):
        try:
            details: PhoneNumberDetails = phone_number_parser.parse(
                candidate,
                country_hint,
            )
        except InvalidPhoneNumberError:
            continue

        return details.e164

    return None


def list_candidate_inputs(raw_number: str) -> list[RawPhoneNumberInput]:
    """The number as given, then WhatsApp-quirk corrections of it."""

    candidates: list[RawPhoneNumberInput] = [to_international_input(raw_number)]
    digits: str = raw_number.strip().removeprefix(PLUS_SIGN)
    if not (digits.isascii() and digits.isdigit()):
        return candidates

    if (
        digits.startswith(BRAZIL_CALLING_CODE)
        and len(digits) == BRAZIL_ID_WITHOUT_NINTH_DIGIT_LENGTH
        and digits[4] in BRAZIL_OLD_MOBILE_FIRST_DIGITS
    ):
        candidates.append(RawPhoneNumberInput(f"+{digits[:4]}9{digits[4:]}"))

    if (
        digits.startswith(MEXICO_OLD_MOBILE_PREFIX)
        and len(digits) == MEXICO_ID_WITH_OLD_PREFIX_LENGTH
    ):
        candidates.append(RawPhoneNumberInput(f"+52{digits[3:]}"))

    return candidates
