"""
Matching conversations with what staff type into the cabinet's search box.

Texts are compared without case and accents in any script (NFKD with the
combining marks removed, then case folding), so "nino" finds "Nino" and
"Ниноʼ", and "jose" finds "José". A phone is matched by its digits in any
format and numeral system: "599 12-34-56", "+995 599 123456", "0599123456"
(national prefix) and Arabic-Indic digits all find "+995599123456".
"""

import unicodedata
from collections.abc import Iterable

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
    prefix of zeros ("0599…", "00995…").
    """

    if phone_number is None or len(digits) < MIN_PHONE_DIGITS:
        return False

    phone_digits: str = digits_of(phone_number)
    if digits in phone_digits:
        return True

    without_prefix: str = digits.lstrip(TRUNK_PREFIX)
    return len(without_prefix) >= MIN_PHONE_DIGITS and without_prefix in phone_digits


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
