"""
New migrations never block writes on tables that already exist
(tests/storage/migration_lint.py; the rules: migrations/README.md).

Files applied before the online-safe pattern (up to 1114) are exempt: they
ran in every environment and can never change (the runner refuses an
edited checksum). Do not add a new file to the list; write it in the
pattern instead: trigger-filled lookup columns, CREATE INDEX CONCURRENTLY
in a `-- workshop:no-transaction` file, backfills with
`workshop backfill-lookup` after the deploy.
"""

from tests.storage.migration_lint import lint_directory, lint_file
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY

APPLIED_BEFORE_THE_ONLINE_PATTERN: frozenset[str] = frozenset(
    {
        "0001_document_collections",
        "0002_channel_and_calendar_collections",
        "0003_payment_collections",
        "0004_widget_lookup_indexes",
        "1010_hot_path_lookup_indexes",
        "1011_leased_job_queue",
        "1020_inbox_and_outbox",
        "1030_worker_heartbeats",
        "1040_attention_count_indexes",
        "1041_rate_limit_buckets",
        "1042_list_pages_and_aggregates",
        "1043_staff_notifications",
        "1044_guided_launch",
        "1051_call_follow_ups",
        "1052_hosted_chat_addresses",
        "1053_team_inbox",
        "1054_website_imports",
        "1061_value_reports",
        "1062_visit_feedback",
        "1063_key_rotations",
        "1071_exchange_rates",
        "1074_product_analytics",
        "1080_activation_follow_up",
        "1081_message_media",
        "1082_two_factor_sign_in",
        "1083_booking_values",
        "1090_reply_speed",
        "1093_platform_alerts_and_incidents",
        "1094_inbound_event_sweep",
        "1100_customer_sources_and_topics",
        "1102_reply_guard_verdicts",
        "1103_sessions_and_support_access",
        "1111_status_page_and_help",
        "1112_teach_from_conversations",
        "1113_exports_and_suppression_list",
        "1114_invoice_numbers_and_billing_details",
    }
)
LAST_EXEMPT_VERSION: str = "1114"
EXISTING: set[str] = {"contacts", "bookings"}
NO_TRANSACTION: str = "-- workshop:no-transaction\n"


def problems(sql_text: str, existing: set[str] | None = None) -> list[str]:
    findings = lint_file(
        "9999_sample", sql_text, EXISTING if existing is None else existing
    )
    return [finding.problem for finding in findings]


def test_new_migrations_never_block_writes_on_existing_tables() -> None:
    findings = lint_directory(MIGRATIONS_DIRECTORY, APPLIED_BEFORE_THE_ONLINE_PATTERN)

    assert [finding.describe() for finding in findings] == []


def test_the_exemptions_are_only_files_applied_before_the_pattern() -> None:
    names = {path.stem for path in MIGRATIONS_DIRECTORY.glob("*.sql")}

    assert names >= APPLIED_BEFORE_THE_ONLINE_PATTERN
    assert all(
        name[:4] <= LAST_EXEMPT_VERSION for name in APPLIED_BEFORE_THE_ONLINE_PATTERN
    )


def test_the_lint_would_have_stopped_the_old_lookup_pattern() -> None:
    old_files = lint_directory(MIGRATIONS_DIRECTORY, frozenset())
    flagged = {finding.migration for finding in old_files}

    assert {"1042_list_pages_and_aggregates", "1053_team_inbox"} <= flagged
    assert "1122_online_lookup_columns" not in flagged


def test_stored_generated_columns_and_plain_indexes_on_old_tables_are_refused() -> None:
    assert problems(
        "alter table workshop.contacts add column if not exists doc_x text\n"
        "    generated always as (document ->> 'x') stored;\n"
        "create index if not exists contacts_x_idx on workshop.contacts (doc_x);\n"
    ) == [
        "a stored generated column on contacts",
        "an index on contacts built without CONCURRENTLY",
    ]


def test_unbatched_data_changes_on_old_tables_are_refused() -> None:
    assert problems(
        "update workshop.bookings set document = document;\n"
        "delete from workshop.contacts where business_id is null;\n"
        "insert into workshop.document_lookup_keys (a)\n"
        "    select 1 from workshop.contacts;\n"
    ) == [
        "an unbatched data change over bookings "
        "(backfill after the deploy: workshop backfill-lookup)",
        "an unbatched data change over contacts "
        "(backfill after the deploy: workshop backfill-lookup)",
        "an unbatched data change over contacts "
        "(backfill after the deploy: workshop backfill-lookup)",
    ]


def test_rewrites_and_full_scans_under_lock_are_refused() -> None:
    assert problems(
        "alter table workshop.contacts alter column document type json;\n"
        "alter table workshop.contacts alter column business_id set not null;\n"
        "alter table workshop.contacts add constraint c check (business_id <> '');\n"
        "alter table workshop.contacts add constraint d check (business_id <> '') "
        "not valid;\n"
    ) == [
        "a column type change on contacts",
        "SET NOT NULL on contacts",
        "a constraint without NOT VALID on contacts",
    ]


def test_tables_created_in_the_same_file_are_free() -> None:
    assert (
        problems(
            "select workshop.create_document_collection('fresh');\n"
            "alter table workshop.fresh add column doc_x text\n"
            "    generated always as (document ->> 'x') stored;\n"
            "create index fresh_x_idx on workshop.fresh (doc_x);\n"
            "update workshop.fresh set document = document;\n"
        )
        == []
    )


def test_no_transaction_files_hold_only_idempotent_statements() -> None:
    assert problems(
        NO_TRANSACTION
        + "select workshop.add_lookup_column('contacts', 'x', 'text');\n"
        + "create index concurrently if not exists contacts_x_idx\n"
        + "    on workshop.contacts (business_id, doc_x);\n"
        + "create or replace function workshop.f() returns int language sql\n"
        + "    as $body$ update workshop.contacts set x = 1; select 1 $body$;\n"
        + "create index concurrently contacts_y_idx on workshop.contacts (doc_y);\n"
        + "alter table workshop.contacts add column z text;\n"
    ) == [
        "a statement a new try could not run again (not idempotent)",
        "a statement a new try could not run again (not idempotent)",
    ]


def test_concurrent_builds_need_a_no_transaction_file() -> None:
    assert problems(
        "begin;\n"
        "create index concurrently if not exists contacts_x_idx "
        "on workshop.contacts (doc_x);\n"
    ) == [
        "transaction control (the runner owns transactions)",
        "CREATE INDEX CONCURRENTLY outside a no-transaction file",
    ]
