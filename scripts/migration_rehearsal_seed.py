"""
The synthetic dataset of a migration rehearsal: production's biggest
document tables filled in proportion (scripts/migration_rehearsal_plan.py,
`DatasetSize`) by `generate_series` inside the database, so millions of rows
take a minute, not an hour of repository writes. Each row is a plausible
document of its collection (ids, the business, timestamps, the fields the
lookup columns and indexes read), spread over `businesses` businesses and
about 30 days; the BEFORE INSERT triggers fill the lookup columns as they
do in production. A table the released schema does not have yet is
skipped. Standard library only.
"""

from collections.abc import Mapping

# 2026-09-01 00:00 UTC in microseconds, the first synthetic write.
FIRST_WRITE_MICROSECONDS: int = 1_788_220_800_000_000
# Rows are spread over 30 days.
SPREAD_MICROSECONDS: int = 30 * 24 * 3600 * 1_000_000

# Per table: the document's own fields as `jsonb_build_object` arguments,
# with {n} the row number and {b} the business expression.
DOCUMENT_FIELDS: Mapping[str, str] = {
    "contacts": (
        "'name', 'Customer ' || n, 'phone_number', '+9955' || lpad(n::text, 8, '0'), "
        "'display_name_folded', 'customer ' || n, 'channel_identities', "
        "'[]'::jsonb, 'last_seen_at', {at}"
    ),
    "conversations": (
        "'contact_id', 'contact_' || n, 'channel', 'whatsapp', 'status', 'open', "
        "'is_sandbox', false, 'last_message_at', {at}"
    ),
    "messages": (
        "'conversation_id', 'conversation_' || (n % {conversations}), 'author', "
        "case when n % 2 = 0 then 'customer' else 'assistant' end, "
        "'text', 'Synthetic message ' || n, 'tool_calls', '[]'::jsonb"
    ),
    "bookings": (
        "'contact_id', 'contact_' || n, 'status', 'confirmed', 'starts_at', {at}, "
        "'ends_at', {at} + 3600000000, 'source_channel', 'whatsapp'"
    ),
    "inbound_events": (
        "'kind', 'customer_message', 'status', 'answered', 'attempts', 1, "
        "'channel', 'whatsapp', 'processed_at', {at} + 4000000"
    ),
    "outbound_messages": (
        "'status', case when n % 50 = 0 then 'dead' else 'delivered' end, "
        "'channel', 'whatsapp', 'attempts', 1"
    ),
}

ROW_SQL: str = """
insert into workshop.{table} (document_key, business_id, document, created_at, updated_at)
select '{prefix}_' || n, {business},
    jsonb_build_object('id', '{prefix}_' || n, 'business_id', {business},
        'created_at', {at}, 'updated_at', {at}, {fields}),
    {at}, {at}
from generate_series(1, {rows}) as n;
"""


def row_time(rows: int) -> str:
    """The n-th row's write time: spread evenly over the 30 days."""

    step: int = max(1, SPREAD_MICROSECONDS // max(1, rows))
    return f"({FIRST_WRITE_MICROSECONDS} + n::bigint * {step})"


def seed_statements(
    rows: Mapping[str, int], businesses: int, existing_tables: set[str]
) -> list[str]:
    """
    The statements that fill the tables of `rows` the schema has, and
    refresh the planner's statistics of each, as production's autovacuum
    keeps them.
    """

    statements: list[str] = ["select set_config('app.bypass_rls', 'on', false)"]
    conversations: int = max(1, rows.get("conversations", 1))
    for table, count in rows.items():
        if table not in existing_tables or table not in DOCUMENT_FIELDS or count < 1:
            continue

        at: str = row_time(count)
        business: str = f"'business_' || (n % {max(1, businesses)})"
        statements.append(
            ROW_SQL.format(
                table=table,
                prefix=table.rstrip("s"),
                business=business,
                at=at,
                rows=count,
                fields=DOCUMENT_FIELDS[table].format(
                    at=at, conversations=conversations
                ),
            ).strip()
        )
        statements.append(f"analyze workshop.{table}")

    return statements
