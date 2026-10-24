"""`workshop seed-load` against a real Postgres, and when it refuses."""

import io
import json
from pathlib import Path

import pytest
from psycopg import sql

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.gateways.cli.seed_load import main
from app.schemas.dto.load_data import LoadSeedManifest
from app.schemas.typings.platform.strings import DatabaseUrl

ENCRYPTION_KEY: str = "seed-load-test-key-0123456789abcdef"  # gitleaks:allow


def count_rows(pool: PostgresConnectionPoolClient, table: str) -> int:
    with pool.transaction() as connection:
        connection.execute("set local app.bypass_rls = 'on'")
        row = connection.execute(
            sql.SQL("select count(*) from {}").format(sql.Identifier("workshop", table))
        ).fetchone()

    assert row is not None
    return int(row[0])


def test_a_small_dataset_is_stored_and_described(
    database_url: DatabaseUrl,
    connection_pool: PostgresConnectionPoolClient,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "load" / "manifest.json"
    output, error_output = io.StringIO(), io.StringIO()
    messages_before = count_rows(connection_pool, "messages")

    exit_code = main(
        [
            "--businesses",
            "2",
            "--messages",
            "300",
            "--bookings",
            "40",
            "--visitors",
            "4",
            "--manifest",
            str(manifest_path),
        ],
        {"DATABASE_URL": database_url, "ENCRYPTION_KEY": ENCRYPTION_KEY},
        output=output,
        error_output=error_output,
    )

    assert exit_code == 0, error_output.getvalue()
    manifest = LoadSeedManifest.model_validate_json(manifest_path.read_text())
    assert len(manifest.businesses) == 2
    assert sum(int(entry.message_count) for entry in manifest.businesses) == 300
    assert manifest.businesses[0].telegram_webhook_secret is not None
    # The bulk history plus each business's month of demo activity.
    assert count_rows(connection_pool, "messages") - messages_before > 300
    assert count_rows(connection_pool, "bookings") >= 40
    assert "Stored 2 businesses with 300 messages, 40 bookings" in output.getvalue()
    assert "Load dataset: 2 of 2 businesses stored." in error_output.getvalue()


def test_a_dash_prints_the_manifest_for_the_caller(database_url: DatabaseUrl) -> None:
    output, error_output = io.StringIO(), io.StringIO()

    exit_code = main(
        ["--businesses", "1", "--messages", "20", "--bookings", "2"]
        + ["--visitors", "1", "--manifest", "-"],
        {"DATABASE_URL": database_url},
        output=output,
        error_output=error_output,
    )

    assert exit_code == 0, error_output.getvalue()
    manifest = LoadSeedManifest.model_validate_json(output.getvalue())
    assert [len(entry.visitors) for entry in manifest.businesses] == [1]
    assert "Manifest: standard output" in error_output.getvalue()


@pytest.mark.parametrize(
    ("arguments", "environment", "reason"),
    [
        ([], {"APP_ENV": "production"}, "refused with APP_ENV=production"),
        ([], {}, "DATABASE_URL is not set"),
        (["--businesses", "0"], {}, "Invalid settings or sizes"),
        (["--messages", "-1"], {}, "Invalid settings or sizes"),
    ],
)
def test_it_refuses_production_memory_and_bad_sizes(
    arguments: list[str],
    environment: dict[str, str],
    reason: str,
    tmp_path: Path,
) -> None:
    error_output = io.StringIO()
    manifest_path = tmp_path / "manifest.json"

    exit_code = main(
        [*arguments, "--manifest", str(manifest_path)],
        environment,
        output=io.StringIO(),
        error_output=error_output,
    )

    assert exit_code == 2
    assert reason in error_output.getvalue()
    assert not manifest_path.exists()


def test_the_manifest_is_plain_json_for_k6(tmp_path: Path) -> None:
    manifest = LoadSeedManifest.model_validate({"seeded_at": 1, "businesses": []})
    path = tmp_path / "manifest.json"
    path.write_text(manifest.model_dump_json())

    assert json.loads(path.read_text()) == {"seeded_at": 1, "businesses": []}
