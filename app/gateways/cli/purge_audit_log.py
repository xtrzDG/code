"""
Remove audit log entries older than a retention period, keeping every hash
chain verifiable.

    workshop purge-audit-log --older-than-days 1095
    workshop purge-audit-log --older-than-days 1095 --batch 2000

(`uv run python -m app.gateways.cli.purge_audit_log ...` without the image.)
The application cannot delete audit entries (migration 1193): this command
calls the database's `workshop.purge_audit_chain`, which runs with the
rights of the role that ran the migrations, refuses a cutoff younger than
365 days, removes the oldest entries of each chain in batches and records
the chain's checkpoint (the last removed position, its hash and the
cutoff). Each chain that lost entries gets a RETENTION_PURGE
entry. Run it with the migration role's DATABASE_URL, never from
`preDeployCommand` (docs/operations/runbooks/audit-chain-broken.md). Exit
codes: 0 done, 1 the purge failed, 2 the arguments or settings are invalid
or DATABASE_URL is not set.
"""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Protocol, TextIO, cast

from dependency_injector import providers
from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.audit_trail import AuditLogPurgeCommand, AuditLogPurgeReport
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.compliance.constrained_integers import AuditPurgeBatchSize
from app.utilities.compliance.audit_retention import (
    MICROSECONDS_PER_DAY,
    MINIMUM_AUDIT_RETENTION_DAYS,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

EXIT_OK: int = 0
EXIT_FAILED: int = 1
EXIT_NOT_CONFIGURED: int = 2
DEFAULT_BATCH: int = 1_000
# Audit entries are kept at least a year (the database's purge function
# refuses a younger cutoff too).
MINIMUM_RETENTION_DAYS: int = int(MINIMUM_AUDIT_RETENTION_DAYS)


class OverridableProvider(Protocol):
    def override(self, provider: object) -> object: ...


def main(
    arguments: Sequence[str] | None = None,
    environment_variables: Mapping[str, str] | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    """Run the purge; returns the process exit code."""

    output_stream: TextIO = sys.stdout if output is None else output
    error_stream: TextIO = sys.stderr if error_output is None else error_output
    parsed: argparse.Namespace = build_argument_parser().parse_args(arguments)
    try:
        settings: AppSettings = assemble_app_settings(
            os.environ if environment_variables is None else environment_variables
        )
        batch_size = AuditPurgeBatchSize(int(parsed.batch))
    except (ApplicationError, ValueError) as error:
        print(f"Invalid arguments or settings: {error}", file=error_stream)
        return EXIT_NOT_CONFIGURED

    if int(parsed.older_than_days) < MINIMUM_RETENTION_DAYS:
        print(
            f"Audit entries are kept at least {MINIMUM_RETENTION_DAYS} days.",
            file=error_stream,
        )
        return EXIT_NOT_CONFIGURED

    if settings.database_url is None:
        print("DATABASE_URL is not set; nothing to purge.", file=error_stream)
        return EXIT_NOT_CONFIGURED

    container = AppContainer()
    cast(OverridableProvider, container.config.app_settings).override(
        providers.Object(settings)
    )
    start: Microseconds = container.time_provider.microsecond_wall_clock().now_unix()
    command = AuditLogPurgeCommand(
        created_before=Microseconds(
            int(start) - int(parsed.older_than_days) * MICROSECONDS_PER_DAY
        ),
        batch_size=batch_size,
    )
    try:
        report: AuditLogPurgeReport = (
            container.operators.audit_trail.purge_audit_log_operator().operate(command)
        )
    except ApplicationError as error:
        print(f"Purge failed: {error}", file=error_stream)
        return EXIT_FAILED
    finally:
        connection_pools = container.clients.postgres_pools()
        if connection_pools is not None:
            connection_pools.close()
        owner_pool = container.clients.postgres_owner_pool()
        if owner_pool is not None:
            owner_pool.close()

    print(
        f"{int(report.entries_removed)} audit entries removed from "
        f"{int(report.chains_purged)} chains.",
        file=output_stream,
    )
    return EXIT_OK


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workshop purge-audit-log",
        description=(
            "Remove audit entries older than the retention period from every "
            "hash chain, keeping each chain verifiable (DATABASE_URL)."
        ),
    )
    parser.add_argument(
        "--older-than-days",
        type=int,
        required=True,
        help=f"remove entries older than this, at least {MINIMUM_RETENTION_DAYS}",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=DEFAULT_BATCH,
        help="entries per statement, 1 to 10000 (default: %(default)s)",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
