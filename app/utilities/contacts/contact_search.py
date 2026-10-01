"""Finding a customer by what the owner remembers about them."""

import unicodedata

from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.contacts.constrained_strings import ContactSearchText

MIN_PHONE_SEARCH_DIGITS: int = 3


def read_search_digits(text: str) -> str:
    """
    The digits of a search as ASCII, from any script (Arabic-Indic,
    Devanagari, fullwidth ...), so "٥٩٩" finds "+995599...".
    """

    return "".join(
        str(unicodedata.decimal(character))
        for character in text
        if character.isdecimal()
    )


def matches_contact_search(
    contact: ContactDocument,
    search: ContactSearchText | None,
) -> bool:
    """
    True when the search is empty, is the contact id, is part of the name
    (any case), or has at least three digits found in one of the phones.
    """

    if search is None:
        return True

    text: str = str(search).strip()
    if text == "" or text == str(contact.id):
        return True

    if contact.name is not None and text.casefold() in str(contact.name).casefold():
        return True

    digits: str = read_search_digits(text)
    if len(digits) < MIN_PHONE_SEARCH_DIGITS:
        return False

    return any(
        phone is not None and digits in read_search_digits(str(phone))
        for phone in (contact.phone_number, contact.verified_phone_number)
    )
