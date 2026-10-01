"""
Finding a customer by what the owner remembers about them, the same way the
conversation feed's search does: the name without case and accents in any
script, and the phone by its digits in any format, also national ones
("0599 12 34 56", "8 916 123-45-67", "07911 123456").
"""

from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.conversations.conversation_search import (
    digits_of,
    normalize_search_text,
    phone_digits_match,
)


def matches_contact_search(
    contact: ContactDocument,
    search: ContactSearchText | None,
    search_phone: E164PhoneNumber | None = None,
) -> bool:
    """
    True when the search is empty, is the contact id, is part of the name
    (without case and accents), is the same number as one of the phones
    (`search_phone`: the search parsed with the business country as a hint),
    or has at least three digits found in one of the phones.
    """

    if search is None:
        return True

    text: str = str(search).strip()
    if text == "" or text == str(contact.id):
        return True

    if contact.name is not None and normalize_search_text(text) in (
        normalize_search_text(str(contact.name))
    ):
        return True

    phones: list[E164PhoneNumber] = [
        phone
        for phone in (contact.phone_number, contact.verified_phone_number)
        if phone is not None
    ]
    if search_phone is not None and search_phone in phones:
        return True

    digits: str = digits_of(text)
    return any(phone_digits_match(digits, str(phone)) for phone in phones)
