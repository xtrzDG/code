"""
The customer list's search, indexed where it can be and bounded where not.

Exact matches come from indexes, however long ago the customer was last
active: the contact id, the full phone number (typed or proved by the
channel) and the exact name without case and accents (the folded-name
lookup of migration 1122). They lead the first page, most recently active
first. Partial matches (part of a name, a few digits of a phone) have no
index: the list is walked most recently active first in keyset batches and
one request looks at most at `SEARCH_SCAN_LIMIT` customers; when it stops
there with room left on the page, its cursor points after the last one it
looked at, so "Load more" searches further back (the page may then hold
fewer rows than asked, even none), as the conversation feed's search does.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.paging import KeysetPosition, KeysetSlice, PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import FoldedContactName
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.contacts.contact_search import (
    fold_contact_name,
    matches_contact_search,
)
from app.utilities.paging.cursor_paging import encode_page_cursor
from app.utilities.paging.keyset_paging import read_slice, single_value_position

SEARCH_BATCH: int = 100
SEARCH_SCAN_LIMIT: int = 500


@dataclass(frozen=True)
class ContactSearchPage:
    """The customers one search request found, and where to go on."""

    contacts: list[ContactDocument]
    next_cursor: PageCursor | None


def search_contacts(
    contact_repo: ContactRepoContract,
    business_id: BusinessId,
    search: ContactSearchText,
    search_phone: E164PhoneNumber | None,
    page: PageRequest,
    accept: Callable[[ContactDocument], bool] = lambda _contact: True,
) -> ContactSearchPage:
    """
    `accept` narrows the matches further (the list's tag, VIP and blocked
    filters).

    Raises:
        ValidationFailedError: the cursor is broken.
    """

    size: int = int(page.size)
    # One row of every page is kept for the walk, so the exact matches a
    # first page shows are the same ones later pages leave out.
    leading: list[ContactDocument] = [
        contact
        for contact in find_exact_matches(
            contact_repo, business_id, search, search_phone
        )
        if accept(contact)
    ][: size - 1]
    shown_ids: set[ContactId] = {contact.id for contact in leading}
    matches: list[ContactDocument] = [] if page.cursor is not None else list(leading)
    after: KeysetPosition | None = read_slice(page).after
    scanned: int = 0
    last_scanned: ContactDocument | None = None
    while scanned < SEARCH_SCAN_LIMIT:
        batch: list[ContactDocument] = contact_repo.page_by_last_seen(
            business_id,
            KeysetSlice(after=after, limit=KeysetReadLimit(SEARCH_BATCH)),
        )
        for contact in batch:
            scanned += 1
            last_scanned = contact
            if (
                contact.id in shown_ids
                or not accept(contact)
                or not matches_contact_search(contact, search, search_phone)
            ):
                continue

            matches.append(contact)
            if len(matches) > size:
                return ContactSearchPage(
                    contacts=matches[:size],
                    next_cursor=cursor_after(matches[size - 1]),
                )

        if len(batch) < SEARCH_BATCH or last_scanned is None:
            return ContactSearchPage(contacts=matches, next_cursor=None)

        after = position_of(last_scanned)

    return ContactSearchPage(
        contacts=matches,
        next_cursor=None if last_scanned is None else cursor_after(last_scanned),
    )


def find_exact_matches(
    contact_repo: ContactRepoContract,
    business_id: BusinessId,
    search: ContactSearchText,
    search_phone: E164PhoneNumber | None,
) -> list[ContactDocument]:
    """
    The customers the search names exactly, most recently active first;
    contacts made only by tests are left out.
    """

    found: dict[ContactId, ContactDocument] = {}
    text: str = str(search).strip()
    candidates: list[ContactDocument | None] = []
    contact_id: ContactId | None = read_contact_id(text)
    if contact_id is not None:
        candidates.append(contact_repo.get(business_id, contact_id))
    if search_phone is not None:
        candidates.append(contact_repo.find_by_phone_number(business_id, search_phone))
        candidates.append(
            contact_repo.find_by_verified_phone_number(business_id, search_phone)
        )
    folded: FoldedContactName | None = fold_contact_name(text)
    if folded is not None:
        candidates.extend(contact_repo.list_by_folded_name(business_id, folded))

    for contact in candidates:
        if contact is not None and contact.last_seen_at is not None:
            found.setdefault(contact.id, contact)

    return sorted(found.values(), key=sort_key, reverse=True)


def read_contact_id(text: str) -> ContactId | None:
    """The search as a contact id, or None when it is not one."""

    try:
        return ContactId(text)
    except ValueError, TypeError:
        return None


def sort_key(contact: ContactDocument) -> tuple[int, str]:
    return (int(contact.last_seen_at or 0), str(contact.id))


def position_of(contact: ContactDocument) -> KeysetPosition:
    return single_value_position(int(contact.last_seen_at or 0), str(contact.id))


def cursor_after(contact: ContactDocument) -> PageCursor:
    return encode_page_cursor(int(contact.last_seen_at or 0), str(contact.id))
