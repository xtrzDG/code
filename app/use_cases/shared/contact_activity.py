"""
A customer's latest activity on their contact: the order of the customer
list (`last_seen_at`, an indexed lookup since migration 1122).

Every path where a customer acts (a message, a call, a missed call, a
booking taken for them) moves it on; to keep a busy conversation from
writing the contact on every message, it moves only when it is at least
`LAST_SEEN_STEP_MICROSECONDS` old. Contacts made only by the owner's test
chat or the autotests are never marked: they stay out of the list.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.domain.contacts import ContactDocument

LAST_SEEN_STEP_MICROSECONDS: int = 5 * 60 * 1_000_000


def mark_contact_seen(contact: ContactDocument, moment: Microseconds) -> bool:
    """Move `last_seen_at` on to `moment`; True when the contact needs saving."""

    if contact.is_test_only:
        return False

    if (
        contact.last_seen_at is not None
        and int(moment) - int(contact.last_seen_at) < LAST_SEEN_STEP_MICROSECONDS
    ):
        return False

    contact.last_seen_at = moment
    return True


def record_contact_seen(
    contact_repo: ContactRepoContract,
    contact: ContactDocument,
    moment: Microseconds,
) -> ContactDocument:
    """Mark the customer seen and save the contact when that moved it."""

    if mark_contact_seen(contact, moment):
        contact_repo.save(contact)

    return contact
