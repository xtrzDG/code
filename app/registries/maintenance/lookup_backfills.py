"""
Which trigger-kept lookup columns of existing tables the post-deploy data
tasks backfill, and which need nothing (the older rows cannot hold the
field). Every `workshop.add_lookup_column` on a table an earlier migration
created is in exactly one of the two lists: a new migration that adds one
fails `tests/architecture_policy/test_lookup_columns_are_backfilled.py`
until it is declared here. Columns of a table created in the same file
are filled by the trigger from the first row and need neither.
"""

from collections.abc import Mapping

from app.schemas.constants.maintenance import IndexedList
from app.schemas.dto.data_tasks import (
    LookupBackfillDeclaration,
    LookupColumnWithoutBackfill,
)
from app.schemas.typings.maintenance.strings import NoBackfillReason
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
    SchemaMigrationName,
)

ONLINE_LOOKUPS: SchemaMigrationName = SchemaMigrationName("1122_online_lookup_columns")
CUSTOMER_CARDS: SchemaMigrationName = SchemaMigrationName(
    "1140_customer_cards_and_segments"
)
SPEND_GUARD: SchemaMigrationName = SchemaMigrationName(
    "1142_spend_guard_and_widget_origins"
)
WAITLIST: SchemaMigrationName = SchemaMigrationName(
    "1151_waitlist_and_rebooking_campaigns"
)
DEPOSITS: SchemaMigrationName = SchemaMigrationName(
    "1190_deposits_and_prepayment_links"
)
BRANDS: SchemaMigrationName = SchemaMigrationName("1192_brands_and_shared_knowledge")
AUDIT_CHAIN: SchemaMigrationName = SchemaMigrationName("1193_append_only_audit_chain")


def backfill(
    collection: str,
    field: str,
    migration: SchemaMigrationName,
    *lists: IndexedList,
) -> LookupBackfillDeclaration:
    return LookupBackfillDeclaration(
        collection_name=DocumentCollectionName(collection),
        field=DocumentFieldPath(field),
        migration=migration,
        lists=list(lists),
    )


def without_backfill(
    collection: str,
    field: str,
    migration: SchemaMigrationName,
    reason: str,
) -> LookupColumnWithoutBackfill:
    return LookupColumnWithoutBackfill(
        collection_name=DocumentCollectionName(collection),
        field=DocumentFieldPath(field),
        migration=migration,
        reason=NoBackfillReason(reason),
    )


CUSTOMERS: IndexedList = IndexedList.CUSTOMERS
KNOWLEDGE: IndexedList = IndexedList.KNOWLEDGE

LOOKUP_BACKFILLS: tuple[LookupBackfillDeclaration, ...] = (
    # The customer list pages by the latest activity, finds exact names and
    # counts a customer's bookings and leads (1122).
    backfill("contacts", "last_seen_at", ONLINE_LOOKUPS, CUSTOMERS),
    backfill("contacts", "display_name_folded", ONLINE_LOOKUPS, CUSTOMERS),
    backfill("bookings", "contact_id", ONLINE_LOOKUPS, CUSTOMERS),
    backfill("leads", "contact_id", ONLINE_LOOKUPS, CUSTOMERS),
    # The knowledge list pages by the latest change, active or not (1122).
    backfill("knowledge_items", "updated_at", ONLINE_LOOKUPS, KNOWLEDGE),
    backfill("knowledge_items", "is_active", ONLINE_LOOKUPS, KNOWLEDGE),
    # Where bookings and leads came from: the value reports' sources (1122).
    backfill("bookings", "source_channel", ONLINE_LOOKUPS),
    backfill("leads", "source_channel", ONLINE_LOOKUPS),
    # The spend guard sums a day's usage by kind, cost and quantity (1142).
    backfill("usage_events", "kind", SPEND_GUARD),
    backfill("usage_events", "cost_micro_usd", SPEND_GUARD),
    backfill("usage_events", "quantity", SPEND_GUARD),
)

LOOKUP_COLUMNS_WITHOUT_BACKFILL: tuple[LookupColumnWithoutBackfill, ...] = (
    without_backfill(
        "contacts",
        "is_vip",
        CUSTOMER_CARDS,
        "Customers written before 1140 have no VIP mark: nobody could set one.",
    ),
    without_backfill(
        "contacts",
        "is_blocked",
        CUSTOMER_CARDS,
        "Customers written before 1140 cannot be blocked: blocking came with it.",
    ),
    without_backfill(
        "bookings",
        "origin",
        WAITLIST,
        "Bookings written before 1151 came from neither the waitlist nor a "
        "campaign, which is what an empty origin means.",
    ),
    without_backfill(
        "bookings",
        "deposit_status",
        DEPOSITS,
        "Bookings written before 1190 never had a deposit asked, which is what "
        "an empty deposit status means.",
    ),
    # The audit log is append-only (1193): a backfill would rewrite its
    # rows, which the table refuses, and none of these needs one.
    without_backfill(
        "audit_log_entries",
        "chain_key",
        AUDIT_CHAIN,
        "Audit entries written before 1193 are in no hash chain.",
    ),
    without_backfill(
        "audit_log_entries",
        "chain_position",
        AUDIT_CHAIN,
        "Audit entries written before 1193 are in no hash chain.",
    ),
    without_backfill(
        "audit_log_entries",
        "security_event",
        AUDIT_CHAIN,
        "Audit entries written before 1193 record no security event.",
    ),
    without_backfill(
        "audit_log_entries",
        "entity_id",
        AUDIT_CHAIN,
        "Only the failed sign-in checks of the last hour are counted by it, "
        "and the trigger fills it for every entry written since 1193.",
    ),
    without_backfill(
        "businesses",
        "brand_id",
        BRANDS,
        "Businesses written before 1192 belong to no brand: brands came with it.",
    ),
)

# The lists that read a collection's documents through columns its
# migration keeps (a document rewritten in the current shape runs the
# lookup trigger): while the migration is open they may miss old rows.
MIGRATION_LISTS: Mapping[DocumentCollectionName, tuple[IndexedList, ...]] = {
    DocumentCollectionName("contacts"): (CUSTOMERS,),
    DocumentCollectionName("knowledge_items"): (KNOWLEDGE,),
}
