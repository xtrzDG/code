"""`workshop backfill-lookup` against a real Postgres and without one."""

import io

from app.gateways.cli.backfill_lookup import main
from tests.storage.postgres_server import ThrowawayPostgresServer


def test_the_command_counts_and_fills(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    environment = {"DATABASE_URL": postgres_server.app_database_url(database_name)}
    dry_output, output = io.StringIO(), io.StringIO()

    dry_code = main(
        ["--collection", "contacts", "--dry-run"], environment, output=dry_output
    )
    code = main(
        ["--collection", "contacts", "--field", "last_seen_at", "--batch", "100"],
        environment,
        output=output,
    )

    assert dry_code == 0
    assert "missing  contacts.last_seen_at: 0 rows" in dry_output.getvalue()
    assert "missing  contacts.display_name_folded: 0 rows" in dry_output.getvalue()
    assert code == 0
    assert "filled   contacts.last_seen_at: 0 of 0 rows in 1 batches" in (
        output.getvalue()
    )


def test_an_unknown_column_exits_with_2(
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    error_output = io.StringIO()

    code = main(
        ["--collection", "contacts", "--field", "phone_number"],
        {"DATABASE_URL": postgres_server.app_database_url(database_name)},
        output=io.StringIO(),
        error_output=error_output,
    )

    assert code == 2
    assert "No trigger fills contacts.phone_number" in error_output.getvalue()


def test_without_a_database_the_command_refuses() -> None:
    error_output = io.StringIO()

    assert main(["--dry-run"], {}, error_output=error_output) == 2
    assert "DATABASE_URL is not set" in error_output.getvalue()


def test_invalid_arguments_exit_with_2() -> None:
    error_output = io.StringIO()

    assert main(["--batch", "0"], {}, error_output=error_output) == 2
    assert main(["--field", "x"], {}, error_output=error_output) == 2
    assert "Invalid arguments" in error_output.getvalue()
