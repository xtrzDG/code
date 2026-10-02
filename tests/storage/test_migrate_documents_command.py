"""`workshop migrate-documents` against a real Postgres, and its arguments."""

import io
import os
import subprocess
import sys

import pytest

from app.gateways.cli.migrate_documents import (
    batch_size,
    build_argument_parser,
    describe_report,
    main,
)
from app.schemas.dto.document_upgrades import (
    CollectionUpgradeReport,
    StoredDocumentsUpgradeReport,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import PROJECT_ROOT_DIRECTORY


def test_a_migrated_database_has_nothing_to_upgrade(database_url: DatabaseUrl) -> None:
    output, error_output = io.StringIO(), io.StringIO()

    exit_code = main(
        ["--collection", "bookings", "--collection", "users", "--batch", "100"],
        {"DATABASE_URL": database_url},
        output=output,
        error_output=error_output,
    )

    assert exit_code == 0
    assert output.getvalue().strip() == (
        "2 collections checked: upgraded 0 documents, 0 failed."
    )
    assert error_output.getvalue() == ""


def test_a_database_without_tables_fails_with_one(
    postgres_server: ThrowawayPostgresServer,
    empty_database_name: str,
) -> None:
    error_output = io.StringIO()

    exit_code = main(
        ["--dry-run", "--collection", "users"],
        {"DATABASE_URL": postgres_server.app_database_url(empty_database_name)},
        output=io.StringIO(),
        error_output=error_output,
    )

    assert exit_code == 1
    assert "Document migration failed" in error_output.getvalue()


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({}, "DATABASE_URL is not set"),
        ({"APP_ENV": "staging-ish"}, "Invalid settings"),
    ],
)
def test_without_a_database_it_explains_and_exits_with_two(
    environment: dict[str, str],
    message: str,
) -> None:
    error_output = io.StringIO()

    exit_code = main([], environment, io.StringIO(), error_output)

    assert exit_code == 2
    assert message in error_output.getvalue()


@pytest.mark.parametrize(
    "arguments",
    [["--collection", "not_a_collection"], ["--batch", "0"], ["--batch", "x"]],
)
def test_bad_arguments_are_refused_by_the_parser(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as stopped:
        build_argument_parser().parse_args(arguments)

    assert stopped.value.code == 2


def test_the_parser_offers_every_catalog_collection() -> None:
    parsed = build_argument_parser().parse_args(
        [f"--collection={definition.name!s}" for definition in DOCUMENT_COLLECTIONS]
    )

    assert len(parsed.collection) == len(DOCUMENT_COLLECTIONS)
    assert batch_size("10000") == 10_000


def test_the_report_lists_collections_with_outdated_rows_and_failures() -> None:
    report = StoredDocumentsUpgradeReport(
        is_dry_run=True,
        collections=[
            CollectionUpgradeReport(
                collection_name=DocumentCollectionName("bookings"),
                current_version=DocumentSchemaVersionNumber(2),
                outdated=DocumentCount(4),
                upgraded=DocumentCount(2),
                newer=DocumentCount(1),
                failed=DocumentCount(1),
                failed_document_keys=[StoredDocumentKey("bkg_1")],
            ),
            CollectionUpgradeReport(
                collection_name=DocumentCollectionName("users"),
                current_version=DocumentSchemaVersionNumber(1),
            ),
        ],
    )

    assert describe_report(report).splitlines() == [
        "bookings (v2): 4 outdated, would upgrade 2, 1 newer left alone, "
        "0 changed meanwhile, 1 failed (bkg_1)",
        "2 collections checked: would upgrade 2 documents, 1 failed.",
    ]


def test_runs_as_a_module() -> None:
    environment = {
        name: value for name, value in os.environ.items() if name != "DATABASE_URL"
    }
    result = subprocess.run(
        [sys.executable, "-m", "app.gateways.cli.migrate_documents", "--dry-run"],
        cwd=PROJECT_ROOT_DIRECTORY,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "DATABASE_URL is not set" in result.stderr
