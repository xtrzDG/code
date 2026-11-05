"""
Which knowledge items mention a customer (PRIV-08): the customer's export
lists them, and their erasure flags them for the owner to review, since
the owner's own text is never changed or deleted by an erasure.

An item mentions the customer when its title, text, attribute values or
aliases hold the customer's name as whole words (without case, accents
and punctuation, as the cabinet's search compares names; also surname
first, "Rossi, Mario"), or one of their numbers in any format: a run of
at least eight digits found in it that is part of their number (national
prefixes dropped as the search does), or a run that holds their whole
number among others ("333 1234567 / 02 7654321"). The platform keeps no
customer e-mail address; their WhatsApp account is a number and matches
as such. A name shorter than three letters matches nothing: it would
flag every item that uses the word.
"""

import re
from collections.abc import Iterator
from contextlib import suppress

import phonenumbers
from phonenumbers import NumberParseException

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
WORD: re.Pattern[str] = re.compile(r"\w+")
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
    """
    The customer's whole name, as words in a row, without case, accents and
    punctuation; also with the last name first.
    """

    if contact.name is None:
        return False

    name: list[str] = words_of(str(contact.name))
    if sum(character.isalpha() for word in name for character in word) < (
        MIN_NAME_LETTERS
    ):
        return False

    written: str = f" {' '.join(words_of(text))} "
    orders: list[list[str]] = [name, [*name[-1:], *name[:-1]]]
    return any(f" {' '.join(order)} " in written for order in orders)


def words_of(text: str) -> list[str]:
    """The words of a text, lower case without accents."""

    return WORD.findall(normalize_search_text(text))


def holds_customer_number(text: str, contact: ContactDocument) -> bool:
    """One of the customer's numbers, written in any format."""

    numbers: list[str] = customer_numbers(contact)
    if not numbers:
        return False

    whole_numbers: list[str] = [
        form for number in numbers for form in whole_number_forms(number)
    ]
    for run in PHONE_RUN.finditer(text):
        digits: str = digits_of(run.group())
        if len(digits) < MIN_MENTIONED_PHONE_DIGITS:
            continue
        if any(phone_digits_match(digits, number) for number in numbers):
            return True
        # Several numbers written as one run: the customer's among them.
        if any(form in digits for form in whole_numbers):
            return True
    return False


def whole_number_forms(number: str) -> list[str]:
    """A number's digits with and without its country code."""

    forms: list[str] = [digits_of(number)]
    with suppress(NumberParseException):
        forms.append(
            phonenumbers.national_significant_number(phonenumbers.parse(number, None))
        )
    return [form for form in forms if len(form) >= MIN_MENTIONED_PHONE_DIGITS]


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
