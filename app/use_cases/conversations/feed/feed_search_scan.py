"""
The feed's search, bounded per request.

Message texts have no search index, so a search walks the feed newest
first in keyset batches and keeps the conversations whose customer name,
phone or message words match. One request looks at most at
`SEARCH_SCAN_LIMIT` conversations; when it stops there with room left on
the page, its cursor points after the last conversation it looked at, so
"Load more" searches older conversations (the page may then hold fewer
rows than asked, even none).
"""

from collections import defaultdict
from dataclasses import dataclass

from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.listing_filters import ConversationFeedFilter
from app.schemas.dto.paging import KeysetPosition, KeysetSlice, PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.utilities.conversations.conversation_search import matches_search
from app.utilities.paging.cursor_paging import encode_page_cursor
from app.utilities.paging.keyset_paging import read_slice, single_value_position

SEARCH_BATCH: int = 100
SEARCH_SCAN_LIMIT: int = 500


@dataclass(frozen=True)
class SearchScan:
    """What one search request found, the contacts it read, and where to go on."""

    matches: list[ConversationDocument]
    contacts: dict[ContactId, ContactDocument]
    next_cursor: PageCursor | None


def scan_feed(
    business_id: BusinessId,
    search: str,
    feed: ConversationFeedFilter,
    page: PageRequest,
    conversation_repo: ConversationRepoContract,
    contact_repo: ContactRepoContract,
    message_repo: MessageRepoContract,
) -> SearchScan:
    """
    Raises:
        ValidationFailedError: the cursor is broken.
    """

    size: int = int(page.size)
    after: KeysetPosition | None = read_slice(page).after
    matches: list[ConversationDocument] = []
    contacts: dict[ContactId, ContactDocument] = {}
    scanned: int = 0
    last_scanned: ConversationDocument | None = None
    while scanned < SEARCH_SCAN_LIMIT:
        batch: list[ConversationDocument] = conversation_repo.page_feed(
            business_id,
            KeysetSlice(after=after, limit=KeysetReadLimit(SEARCH_BATCH)),
            feed,
        )
        batch_contacts = contact_repo.get_many(
            business_id, [conversation.contact_id for conversation in batch]
        )
        texts: dict[ConversationId, list[str]] = message_texts(
            business_id, batch, message_repo
        )
        for conversation in batch:
            scanned += 1
            last_scanned = conversation
            contact: ContactDocument | None = batch_contacts.get(
                conversation.contact_id
            )
            if is_match(search, contact, texts.get(conversation.id, [])):
                matches.append(conversation)
                if contact is not None:
                    contacts[contact.id] = contact
                if len(matches) > size:
                    return SearchScan(
                        matches=matches[:size],
                        contacts=contacts,
                        next_cursor=cursor_after(matches[size - 1]),
                    )

        if len(batch) < SEARCH_BATCH or last_scanned is None:
            return SearchScan(matches=matches, contacts=contacts, next_cursor=None)

        after = single_value_position(
            int(last_scanned.last_message_at), str(last_scanned.id)
        )

    return SearchScan(
        matches=matches,
        contacts=contacts,
        next_cursor=None if last_scanned is None else cursor_after(last_scanned),
    )


def message_texts(
    business_id: BusinessId,
    conversations: list[ConversationDocument],
    message_repo: MessageRepoContract,
) -> dict[ConversationId, list[str]]:
    grouped: defaultdict[ConversationId, list[str]] = defaultdict(list[str])
    messages: list[MessageDocument] = message_repo.list_by_conversations(
        business_id, [conversation.id for conversation in conversations]
    )
    for message in messages:
        grouped[message.conversation_id].append(str(message.text))

    return dict(grouped)


def is_match(search: str, contact: ContactDocument | None, texts: list[str]) -> bool:
    return matches_search(
        search,
        None if contact is None or contact.name is None else str(contact.name),
        None
        if contact is None or contact.phone_number is None
        else str(contact.phone_number),
        texts,
    )


def cursor_after(conversation: ConversationDocument) -> PageCursor:
    return encode_page_cursor(int(conversation.last_message_at), str(conversation.id))
