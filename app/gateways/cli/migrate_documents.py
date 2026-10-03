"""
Rewrite stored documents of older schema versions in the current shape.

    workshop migrate-documents                          # every collection
    workshop migrate-documents --collection bookings --batch 500
    workshop migrate-documents --dry-run                # only count

(`uv run python -m app.gateways.cli.migrate_documents ...` without the
image.) Run it after a release that bumped a document's `schema_version` is
fully deployed; docs/operations/deploys.md says when. It works platform-wide
(row-level security bypassed), batch by batch, and is idempotent. Exit codes:
0 done, 1 some documents could not be upgraded or the database failed,
2 DATABASE_URL is not set or the settings are invalid.
"""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from typing import TextIO

from app.adapters.storage.postgres.postgres_stored_document_upgrade_adapter import (
    PostgresStoredDocumentUpgradeAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.document_upgrades import (
    DEFAULT_UPGRADE_BATCH_SIZE,
    CollectionUpgradeReport,
    StoredDocumentsUpgradeReport,
    UpgradeStoredDocumentsCommand,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.storage.constrained_integers import (
    DocumentUpgradeBatchSize,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.use_cases.maintenance.upgrade_stored_documents_use_case import (
    UpgradeStoredDocumentsUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS

EXIT_OK: int = 0
EXIT_FAILED: int = 1
EXIT_NOT_CONFIGURED: int = 2


def main(
    arguments: Sequence[str] | None = None,
    environment_variables: Mapping[str, str] | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    """Run the upgrade; returns the process exit code."""

    output_stream: TextIO = sys.stdout if output is None else output
    error_stream: TextIO = sys.stderr if error_output is None else error_output
    parsed_arguments: argparse.Namespace = build_argument_parser().parse_args(arguments)
    requested_names: list[str] = list(parsed_arguments.collection or [])
    command = UpgradeStoredDocumentsCommand(
        collection_names=[DocumentCollectionName(name) for name in requested_names],
        batch_size=DocumentUpgradeBatchSize(int(parsed_arguments.batch)),
        is_dry_run=bool(parsed_arguments.dry_run),
    )
    try:
        settings: AppSettings = assemble_app_settings(
            os.environ if environment_variables is None else environment_variables
        )
    except (ApplicationError, ValueError) as error:
        print(f"Invalid settings: {error}", file=error_stream)
        return EXIT_NOT_CONFIGURED

    if settings.database_url is None:
        print(
            "DATABASE_URL is not set; in-memory storage has no stored documents.",
            file=error_stream,
        )
        return EXIT_NOT_CONFIGURED

    connection_pool = PostgresConnectionPoolClient(
        database_url=settings.database_url,
        max_size=1,
        application_name="assistant-workshop-migrate-documents",
        # One batch of rewritten documents per statement: longer than a
        # request, bounded all the same.
        statement_timeout_seconds=5 * 60,
        idle_in_transaction_timeout_seconds=5 * 60,
    )
    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                UpgradeStoredDocumentsUseCase(
                    document_upgrades=PostgresStoredDocumentUpgradeAdapter(
                        connection_pool
                    )
                )
            )
        )
    )
    try:
        report: StoredDocumentsUpgradeReport = operator.operate(command)
    except ApplicationError as error:
        print(f"Document migration failed: {error}", file=error_stream)
        return EXIT_FAILED
    finally:
        connection_pool.close()

    print(describe_report(report), file=output_stream)
    has_failures: bool = any(int(entry.failed) > 0 for entry in report.collections)
    return EXIT_FAILED if has_failures else EXIT_OK


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workshop migrate-documents",
        description=(
            "Rewrite stored documents of older schema versions in the current "
            "shape (DATABASE_URL, all businesses)."
        ),
    )
    parser.add_argument(
        "--collection",
        action="append",
        choices=[str(definition.name) for definition in DOCUMENT_COLLECTIONS],
        metavar="NAME",
        help="only this collection (repeatable; default: every collection)",
    )
    parser.add_argument(
        "--batch",
        type=batch_size,
        default=int(DEFAULT_UPGRADE_BATCH_SIZE),
        help="rows per transaction, 1 to 10000 (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="only count what would be upgraded",
    )
    return parser


def batch_size(text: str) -> int:
    """argparse type of --batch: a whole number from 1 to 10000."""

    try:
        return int(DocumentUpgradeBatchSize(int(text)))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not a whole number from 1 to 10000"
        ) from error


def describe_report(report: StoredDocumentsUpgradeReport) -> str:
    """One line per collection with outdated rows, then a total."""

    verb: str = "would upgrade" if report.is_dry_run else "upgraded"
    lines: list[str] = [
        describe_collection(entry, verb)
        for entry in report.collections
        if int(entry.outdated) > 0
    ]
    total: int = sum(int(entry.upgraded) for entry in report.collections)
    failed: int = sum(int(entry.failed) for entry in report.collections)
    lines.append(
        f"{len(report.collections)} collections checked: {verb} {total} "
        f"documents, {failed} failed."
    )
    return "\n".join(lines)


def describe_collection(entry: CollectionUpgradeReport, verb: str) -> str:
    line: str = (
        f"{entry.collection_name!s} (v{int(entry.current_version)}): "
        f"{int(entry.outdated)} outdated, {verb} {int(entry.upgraded)}, "
        f"{int(entry.newer)} newer left alone, "
        f"{int(entry.changed_meanwhile)} changed meanwhile, "
        f"{int(entry.failed)} failed"
    )
    if entry.failed_document_keys:
        line += " (" + ", ".join(str(key) for key in entry.failed_document_keys)
        line += ")"

    return line


if __name__ == "__main__":
    raise SystemExit(main())
