"""
Migration 1053 on a database with history: conversations with a new or
in-progress request get `has_open_request`, those with a request open or a
person needed get `awaits_team`, the rest stay as they were.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from psycopg import Connection, sql
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.storage.migration_steps import run_migrations
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY

TEAM_INBOX_MIGRATION: str = "1053_team_inbox.sql"


def copy_migrations_before_team_inbox(target_directory: Path) -> Path:
    target_directory.mkdir()
    for source_path in MIGRATIONS_DIRECTORY.glob("*.sql"):
        if source_path.name < TEAM_INBOX_MIGRATION:
            target_directory.joinpath(source_path.name).write_bytes(
                source_path.read_bytes()
            )

    return target_directory


def test_team_inbox_migration_marks_the_conversations_that_wait(
    postgres_server: ThrowawayPostgresServer,
    tmp_path: Path,
) -> None:
    migrations = copy_migrations_before_team_inbox(tmp_path / "migrations")
    database_name = postgres_server.create_database()
    database_url = postgres_server.app_database_url(database_name)
    try:
        run_migrations(database_url, migrations)
        business_id = str(BusinessId())
        conversations = {
            "handoff": {"status": "handoff"},
            "new_request": {"status": "open"},
            "request_in_progress": {"status": "closed"},
            "won_request": {"status": "open"},
            "quiet": {"status": "open"},
        }
        leads = {
            "lead_new": ("new_request", "new"),
            "lead_working": ("request_in_progress", "in_progress"),
            "lead_won": ("won_request", "won"),
        }
        with postgres_server.admin_connection(database_name) as connection:
            for key, document in conversations.items():
                insert(connection, "conversations", key, business_id, document)
            for key, (conversation_key, status) in leads.items():
                insert(
                    connection,
                    "leads",
                    key,
                    business_id,
                    {"conversation_id": conversation_key, "status": status},
                )

        migrations.joinpath(TEAM_INBOX_MIGRATION).write_bytes(
            MIGRATIONS_DIRECTORY.joinpath(TEAM_INBOX_MIGRATION).read_bytes()
        )
        report = run_migrations(database_url, migrations)

        with postgres_server.admin_connection(database_name) as connection:
            rows = connection.execute(
                "select document_key, document, doc_awaits_team, doc_assignee_user_id "
                "from workshop.conversations order by document_key"
            ).fetchall()
            collections = connection.execute(
                "select count(*) from information_schema.tables "
                "where table_schema = 'workshop' and table_name in "
                "('conversation_notes', 'quick_reply_libraries', 'inbox_settings')"
            ).fetchone()
    finally:
        postgres_server.drop_database(database_name)

    assert [str(name) for name in report.newly_applied] == ["1053_team_inbox"]
    stored: dict[str, dict[str, Any]] = {str(row[0]): row[1] for row in rows}
    marked = {key: document.get("has_open_request") for key, document in stored.items()}
    assert marked == {
        "handoff": None,
        "new_request": True,
        "quiet": None,
        "request_in_progress": True,
        "won_request": None,
    }
    assert {str(row[0]): row[2] for row in rows} == {
        "handoff": "true",
        "new_request": "true",
        "quiet": None,
        "request_in_progress": "true",
        "won_request": None,
    }
    assert {row[3] for row in rows} == {None}
    assert collections is not None and collections[0] == 3


def insert(
    connection: Connection[TupleRow],
    table: str,
    key: str,
    business_id: str,
    document: Mapping[str, object],
) -> None:
    connection.execute(
        sql.SQL(
            "insert into {} (document_key, business_id, document, created_at, "
            "updated_at) values (%s, %s, %s, 1, 1)"
        ).format(sql.Identifier("workshop", table)),
        (key, business_id, Jsonb(dict(document))),
    )
