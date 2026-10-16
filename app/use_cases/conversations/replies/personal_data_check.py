"""
The personal data check of a reply: another person's phone number or
e-mail address never reaches a customer.

A phone number of the reply is fine when it is the customer's own, or
appears in what the business published (the facts, tool results, the
context line) or in what this customer wrote; otherwise it is looked up
among the business's contacts (the indexed phone lookups), and a number
that belongs to another contact is withheld. An e-mail address must come
from the same places: the platform keeps no customer e-mails, so an
address from anywhere else (a staff message quoting another customer, or
an invented one) is withheld too.
"""

from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.use_cases.conversations.replies.reply_evidence import ReplyEvidence
from app.utilities.reply_guard.contact_details import (
    FoundPhone,
    find_email_addresses,
    find_phone_numbers,
)


def find_withheld_contact_details(
    contact_repo: ContactRepoContract,
    turn: PreparedTurn,
    text: str,
    evidence: ReplyEvidence,
) -> list[str]:
    """Phone numbers and e-mail addresses of the reply to withhold, as written."""

    country: CountryCode = turn.business.country_code
    phones: list[FoundPhone] = find_phone_numbers(text, country)
    emails: list[str] = find_email_addresses(text)
    if not phones and not emails:
        return []

    published_phones: set[E164PhoneNumber] = {
        phone.e164
        for evidence_text in evidence.own_contact
        for phone in find_phone_numbers(evidence_text, country)
    }
    published_emails: set[str] = {
        email
        for evidence_text in evidence.own_contact
        for email in find_email_addresses(evidence_text)
    }
    own_phones: set[E164PhoneNumber | None] = {
        turn.contact.phone_number,
        turn.contact.verified_phone_number,
    }
    withheld: list[str] = []
    for phone in phones:
        if phone.e164 in own_phones or phone.e164 in published_phones:
            continue

        if is_another_contacts_phone(contact_repo, turn, phone.e164):
            withheld.append(phone.text)

    withheld.extend(email for email in emails if email not in published_emails)
    return withheld


def is_another_contacts_phone(
    contact_repo: ContactRepoContract,
    turn: PreparedTurn,
    phone: E164PhoneNumber,
) -> bool:
    """Whether a contact of the business other than this customer has it."""

    owners: list[ContactDocument | None] = [
        contact_repo.find_by_phone_number(turn.business.id, phone),
        contact_repo.find_by_verified_phone_number(turn.business.id, phone),
    ]
    return any(
        owner is not None and owner.id != turn.contact.id and owner.erased_at is None
        for owner in owners
    )
