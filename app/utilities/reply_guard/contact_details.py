"""
Phone numbers and e-mail addresses written in a text, for the personal
data check of a reply: phones read with libphonenumber in the business's
country (local formats too), e-mail addresses with a plain matcher.
"""

import re
from dataclasses import dataclass

import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneNumberMatch

from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.utilities.reply_guard.numerals import normalize_digits

EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![\w.+-])[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63})*\.[^\W\d_]{2,24}(?![\w-])"
)
MAX_SCANNED_CHARACTERS: int = 8000


@dataclass(frozen=True)
class FoundPhone:
    """A phone number of a text as written and in E.164 (technical record)."""

    text: str
    e164: E164PhoneNumber


def find_phone_numbers(text: str, country: CountryCode) -> list[FoundPhone]:
    """Valid phone numbers of the text, local ones read in the country."""

    normalized_text: str = normalize_digits(text[:MAX_SCANNED_CHARACTERS])
    found: list[FoundPhone] = []
    matcher = phonenumbers.PhoneNumberMatcher(
        normalized_text, str(country), leniency=phonenumbers.Leniency.VALID
    )
    for match in matcher:
        phone_match: PhoneNumberMatch = match
        found.append(
            FoundPhone(
                text=phone_match.raw_string,
                e164=E164PhoneNumber(
                    phonenumbers.format_number(
                        phone_match.number, PhoneNumberFormat.E164
                    )
                ),
            )
        )

    return found


def find_email_addresses(text: str) -> list[str]:
    """E-mail addresses of the text, lower case, in order, without repeats."""

    addresses: list[str] = []
    for match in EMAIL_PATTERN.finditer(text[:MAX_SCANNED_CHARACTERS]):
        address: str = match.group(0).lower()
        if address not in addresses:
            addresses.append(address)

    return addresses
