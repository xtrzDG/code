"""
Matching conversations with what staff type into the cabinet's search box.

Texts are compared without case and accents in any script (NFKD with the
combining marks removed, then case folding), so "nino" finds "Nino" and
"Ниноʼ", and "jose" finds "José". A phone is matched by its digits in any
format and numeral system: "599 12-34-56", "+995 599 123456", "0599123456"
(national prefix) and Arabic-Indic digits all find "+995599123456"; the
national prefix of the phone's own country is dropped too ("8 916 …" finds
"+79161234567", "06 30 …" finds "+3630…").
"""

import re
import unicodedata
from collections.abc import Iterable

import phonenumbers
from phonenumbers import NumberParseException, PhoneMetadata

MIN_PHONE_DIGITS: int = 3
PHONE_PUNCTUATION: frozenset[str] = frozenset(" +-(). /")
TRUNK_PREFIX: str = "0"


def normalize_search_text(text: str) -> str:
    """Lower case without accents and with single spaces, in any script."""

    decomposed: str = unicodedata.normalize("NFKD", text)
    without_marks: str = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(without_marks.casefold().split())


def digits_of(text: str) -> str:
    """The decimal digits of a text as ASCII, in any numeral system."""

    return "".join(
        str(unicodedata.decimal(character))
        for character in text
        if character.isdecimal()
    )


def looks_like_phone(text: str) -> bool:
    """Only digits and phone punctuation, with enough digits to search by."""

    return len(digits_of(text)) >= MIN_PHONE_DIGITS and all(
        character.isdecimal() or character in PHONE_PUNCTUATION
        for character in text.strip()
    )


def phone_digits_match(digits: str, phone_number: str | None) -> bool:
    """
    The digits appear in the phone, also without a national or international
    prefix of zeros ("0599…", "00995…") or without the national prefix of
    the phone's own country ("8 916…" for +7, "06 30…" for +36).
    """

    if phone_number is None or len(digits) < MIN_PHONE_DIGITS:
        return False

    phone_digits: str = digits_of(phone_number)
    if digits in phone_digits:
        return True

    return any(
        len(candidate) >= MIN_PHONE_DIGITS and candidate in phone_digits
        for candidate in (
            digits.lstrip(TRUNK_PREFIX),
            without_national_prefix(digits, phone_number),
        )
    )


def without_national_prefix(digits: str, phone_number: str) -> str:
    """
    The digits without the trunk prefix of the phone's own country (libphonenumber
    metadata: "8" for +7 and +375, "0" for +995, "06" for +36), also for
    partial numbers; unchanged when the phone's country has none.
    """

    try:
        region: str | None = phonenumbers.region_code_for_number(
            phonenumbers.parse(phone_number, None)
        )
    except NumberParseException:
        return digits

    metadata: PhoneMetadata | None = (
        None if region is None else PhoneMetadata.metadata_for_region(region)
    )
    if metadata is None or not metadata.national_prefix_for_parsing:
        return digits

    prefix: re.Match[str] | None = re.match(
        metadata.national_prefix_for_parsing, digits
    )
    return digits if prefix is None else digits[prefix.end() :]


def matches_search(
    search: str,
    contact_name: str | None,
    phone_number: str | None,
    texts: Iterable[str],
) -> bool:
    """
    Does a conversation match the search? A phone-like search matches the
    phone by digits. Otherwise every word must appear in the name or a
    message, or (with three or more digits) in the phone.
    """

    if looks_like_phone(search) and phone_digits_match(digits_of(search), phone_number):
        return True

    words: list[str] = normalize_search_text(search).split()
    if not words:
        return True

    haystack: str = normalize_search_text(" ".join([contact_name or "", *texts]))
    return all(
        word in haystack or phone_digits_match(digits_of(word), phone_number)
        for word in words
    )
