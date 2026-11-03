"""
Which knowledge items mention a customer (PRIV-08): the customer's export
lists them, and their erasure flags them for the owner to review, since
the owner's own text is never changed or deleted by an erasure.

An item mentions the customer when its title, text, attribute values or
aliases hold the customer's name as whole words (without case and accents,
as the cabinet's search compares names), or one of their numbers in any
format (a run of at least eight digits found in it, national prefixes
dropped as the search does). The platform keeps no customer e-mail
address; their WhatsApp account is a number and matches as such.
A name shorter than three letters matches nothing: it would flag every
item that uses the word.
"""

import re
from collections.abc import Iterator

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.privacy import KnowledgeMentionMatch
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.utilities.conversations.conversation_search import (
    digits_of,
    normalize_search_text,
    phone_digits_match,
)

MIN_NAME_LETTERS: int = 3
MIN_MENTIONED_PHONE_DIGITS: int = 8
# A run of digits with the punctuation phone numbers are written with.
PHONE_RUN: re.Pattern[str] = re.compile(r"\+?\d[\d \t().\-/]{6,}\d")
NUMBER_CHANNELS: frozenset[ChannelKind] = frozenset({ChannelKind.WHATSAPP})


def mention_matches(
    item: KnowledgeItemDocument, contact: ContactDocument
) -> list[KnowledgeMentionMatch]:
    """How the item mentions the customer: by name, by number, both or not."""

    texts: list[str] = list(item_texts(item))
    matches: list[KnowledgeMentionMatch] = []
    if any(names_customer(text, contact) for text in texts):
        matches.append(KnowledgeMentionMatch.NAME)
    if any(holds_customer_number(text, contact) for text in texts):
        matches.append(KnowledgeMentionMatch.PHONE)
    return matches


def item_texts(item: KnowledgeItemDocument) -> Iterator[str]:
    """Every text of the item the owner wrote or imported."""

    yield str(item.title)
    if item.body is not None:
        yield str(item.body)
    for attribute in item.attributes:
        yield str(attribute.value)
    for alias in item.aliases:
        yield str(alias.text)


def names_customer(text: str, contact: ContactDocument) -> bool:
    """The customer's whole name, as words, without case and accents."""

    if contact.name is None:
        return False

    name: str = normalize_search_text(str(contact.name))
    if sum(character.isalpha() for character in name) < MIN_NAME_LETTERS:
        return False

    pattern: str = rf"(?<!\w){re.escape(name)}(?!\w)"
    return re.search(pattern, normalize_search_text(text)) is not None


def holds_customer_number(text: str, contact: ContactDocument) -> bool:
    """One of the customer's numbers, written in any format."""

    numbers: list[str] = customer_numbers(contact)
    if not numbers:
        return False

    for run in PHONE_RUN.finditer(text):
        digits: str = digits_of(run.group())
        if len(digits) < MIN_MENTIONED_PHONE_DIGITS:
            continue
        if any(phone_digits_match(digits, number) for number in numbers):
            return True
    return False


def customer_numbers(contact: ContactDocument) -> list[str]:
    """The customer's phones and the number of their WhatsApp account."""

    numbers: list[str] = [
        str(phone)
        for phone in (contact.phone_number, contact.verified_phone_number)
        if phone is not None
    ]
    numbers.extend(
        f"+{digits_of(str(identity.channel_user_id))}"
        for identity in contact.channel_identities
        if identity.channel in NUMBER_CHANNELS
        and len(digits_of(str(identity.channel_user_id))) >= MIN_MENTIONED_PHONE_DIGITS
    )
    return list(dict.fromkeys(numbers))
