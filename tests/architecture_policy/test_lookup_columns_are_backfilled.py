"""
Every trigger-kept lookup column added to a table that already held rows
is filled after the deploy by a data task, or says why nothing needs it.

`workshop.add_lookup_column` fills the column for rows written from then
on; rows of an earlier migration's table stay empty until the backfill
runs, and a list that pages by the column would miss them. The data-task
registry (`app/registries/maintenance/lookup_backfills.py`) declares each
such column once: in `LOOKUP_BACKFILLS` (the batch worker fills it) or in
`LOOKUP_COLUMNS_WITHOUT_BACKFILL` (with the reason). Columns of a table
created in the same migration need neither.
"""

import re
from pathlib import Path

from app.registries.maintenance.lookup_backfills import (
    LOOKUP_BACKFILLS,
    LOOKUP_COLUMNS_WITHOUT_BACKFILL,
)
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS

MIGRATIONS: Path = Path(__file__).resolve().parents[2] / "migrations"
CREATED_TABLE: re.Pattern[str] = re.compile(
    r"^select workshop\.create_document_collection\('(?P<table>[a-z_0-9]+)'\);",
    re.MULTILINE,
)
ADDED_COLUMN: re.Pattern[str] = re.compile(
    r"^select workshop\.add_lookup_column\(\s*'(?P<table>[a-z_0-9]+)',\s*"
    r"'(?P<field>[a-z_0-9]+)'",
    re.MULTILINE,
)

type Column = tuple[str, str, str]


def columns_added_to_existing_tables() -> set[Column]:
    """(table, field, migration) of each lookup column of an older table."""

    created: dict[str, str] = {}
    added: set[Column] = set()
    for path in sorted(MIGRATIONS.glob("*.sql")):
        text: str = path.read_text(encoding="utf-8")
        for match in CREATED_TABLE.finditer(text):
            created.setdefault(match["table"], path.stem)
        for match in ADDED_COLUMN.finditer(text):
            if created.get(match["table"], path.stem) != path.stem:
                added.add((match["table"], match["field"], path.stem))

    return added


def declared_columns() -> list[Column]:
    return [
        (str(item.collection_name), str(item.field), str(item.migration))
        for item in (*LOOKUP_BACKFILLS, *LOOKUP_COLUMNS_WITHOUT_BACKFILL)
    ]


def test_every_lookup_column_of_an_older_table_is_declared_once() -> None:
    declared: list[Column] = declared_columns()

    assert sorted(set(declared)) == sorted(declared), "A column is declared twice."
    assert set(declared) == columns_added_to_existing_tables(), (
        "A migration adds a lookup column to a table an earlier migration "
        "created: declare it in app/registries/maintenance/lookup_backfills.py "
        "(LOOKUP_BACKFILLS, or LOOKUP_COLUMNS_WITHOUT_BACKFILL with the reason)."
    )


def test_the_parser_sees_the_columns_of_migration_1122() -> None:
    added: set[Column] = columns_added_to_existing_tables()

    assert ("contacts", "last_seen_at", "1122_online_lookup_columns") in added
    # client_standings is created by 1122 itself: the trigger fills it.
    assert not any(table == "client_standings" for table, _, _ in added)


def test_backfilled_columns_are_of_stored_collections() -> None:
    collections: set[str] = {str(item.name) for item in DOCUMENT_COLLECTIONS}

    assert {table for table, _, _ in declared_columns()} <= collections
