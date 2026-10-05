"""
The customer list and the knowledge list on the trigger-kept lookups of
migration 1122, and the index each statement must use.
"""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import FoldedContactName
from tests.storage.list_query_plans import (
    BUSINESS,
    FIRST_PAGE,
    LATER_PAGE,
    ListQuery,
)

LOOKUP_LIST_QUERIES: tuple[ListQuery, ...] = (
    ListQuery(
        "customers, most recently active first",
        lambda r: r.contacts.page_by_last_seen(BUSINESS, FIRST_PAGE),
        "contacts",
        "contacts_doc_last_seen_at_idx",
    ),
    ListQuery(
        "customers, a later page",
        lambda r: r.contacts.page_by_last_seen(BUSINESS, LATER_PAGE),
        "contacts",
        "contacts_doc_last_seen_at_idx",
    ),
    ListQuery(
        "customers of one exact name",
        lambda r: r.contacts.list_by_folded_name(
            BUSINESS, FoldedContactName("customer 4520")
        ),
        "contacts",
        "contacts_doc_display_name_folded_idx",
    ),
    ListQuery(
        "conversations, bookings and leads of a page of customers",
        lambda r: r.contact_activity.count_for_contacts(
            BUSINESS, [ContactId() for _ in range(50)]
        ),
        "bookings",
        "bookings_doc_contact_id_idx",
        ("conversations_doc_contact_idx", "leads_doc_contact_id_idx"),
        ("conversations", "leads"),
    ),
    ListQuery(
        "knowledge base, last changed first",
        lambda r: r.knowledge.page_by_business(BUSINESS, FIRST_PAGE, None, None),
        "knowledge_items",
        "knowledge_items_doc_updated_at_idx",
    ),
    ListQuery(
        "knowledge of one kind, a later page",
        lambda r: r.knowledge.page_by_business(
            BUSINESS, LATER_PAGE, KnowledgeItemKind.FAQ, None
        ),
        "knowledge_items",
        "knowledge_items_doc_kind_updated_at_idx",
    ),
)
