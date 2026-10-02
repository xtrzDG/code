"""
Store a load-test dataset and write the manifest the load tests read.

    workshop seed-load --manifest perf/manifest.json     # the weekly scale
    workshop seed-load --businesses 20 --messages 40000 --bookings 4000 \\
        --visitors 100 --manifest /tmp/manifest.json

(`uv run python -m app.gateways.cli.seed_load ...` without the image.) The
default scale is the weekly perf run's: 500 businesses, 2,000,000 messages,
200,000 bookings and 1,000 website-widget visitors. Every business is a
demo business with its own signed-in owner plus a bulk history; the
manifest (JSON) names the businesses, the owners' bearer tokens, recent
conversations, widget visitors and Telegram webhook secrets, so keep it
with the load-test database (docs/operations/capacity.md).

Needs DATABASE_URL and is refused with APP_ENV=production: the dataset is
made up and the tokens are real sessions. Exit codes: 0 stored, 1 storing
failed, 2 not configured or refused.
"""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO

from dependency_injector import providers

from app.containers.app import AppContainer
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.dto.load_data import LoadSeedManifest, SeedLoadCommand
from app.schemas.exceptions.base_exception import ApplicationError
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.observability.logging_setup import configure_logging

EXIT_OK: int = 0
EXIT_FAILED: int = 1
EXIT_NOT_CONFIGURED: int = 2
DEFAULT_MANIFEST_PATH: str = "perf/manifest.json"


def main(
    arguments: Sequence[str] | None = None,
    environment_variables: Mapping[str, str] | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    """Store the dataset; returns the process exit code."""

    output_stream: TextIO = sys.stdout if output is None else output
    error_stream: TextIO = sys.stderr if error_output is None else error_output
    parsed: argparse.Namespace = build_argument_parser().parse_args(arguments)
    try:
        command = SeedLoadCommand.model_validate(
            {
                "business_count": parsed.businesses,
                "message_count": parsed.messages,
                "booking_count": parsed.bookings,
                "visitor_count": parsed.visitors,
                "random_seed": parsed.seed,
            }
        )
        settings: AppSettings = assemble_app_settings(
            os.environ if environment_variables is None else environment_variables
        )
    except (ApplicationError, ValueError) as error:
        print(f"Invalid settings or sizes: {error}", file=error_stream)
        return EXIT_NOT_CONFIGURED

    refusal: str | None = refuse(settings)
    if refusal is not None:
        print(refusal, file=error_stream)
        return EXIT_NOT_CONFIGURED

    configure_logging(settings.log_format, stream=error_stream)
    container = AppContainer()
    container.config.app_settings.override(providers.Object(settings))
    try:
        manifest: LoadSeedManifest = (
            container.operators.demo.seed_load_operator().operate(command)
        )
    except ApplicationError as error:
        print(f"Storing the load dataset failed: {error}", file=error_stream)
        return EXIT_FAILED
    finally:
        connection_pool = container.clients.postgres_pool()
        if connection_pool is not None:
            connection_pool.close()

    manifest_path = Path(parsed.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    print(describe_manifest(manifest, manifest_path), file=output_stream)
    return EXIT_OK


def refuse(settings: AppSettings) -> str | None:
    """Why this deployment may not get a load dataset (None: it may)."""

    if settings.environment is DeploymentEnvironment.PRODUCTION:
        return "seed-load is refused with APP_ENV=production."

    if settings.database_url is None:
        return "DATABASE_URL is not set; a load dataset needs Postgres."

    return None


def build_argument_parser() -> argparse.ArgumentParser:
    defaults = SeedLoadCommand()
    parser = argparse.ArgumentParser(
        prog="workshop seed-load",
        description=(
            "Store a load-test dataset in DATABASE_URL and write its manifest "
            "(never in production)."
        ),
    )
    parser.add_argument("--businesses", type=int, default=int(defaults.business_count))
    parser.add_argument("--messages", type=int, default=int(defaults.message_count))
    parser.add_argument("--bookings", type=int, default=int(defaults.booking_count))
    parser.add_argument(
        "--visitors",
        type=int,
        default=int(defaults.visitor_count),
        help="website-widget visitors with a conversation (default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=int(defaults.random_seed),
        help="the same seed builds the same history (default: %(default)s)",
    )
    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST_PATH,
        help="where the JSON manifest goes (default: %(default)s)",
    )
    return parser


def describe_manifest(manifest: LoadSeedManifest, path: Path) -> str:
    messages: int = sum(int(entry.message_count) for entry in manifest.businesses)
    bookings: int = sum(int(entry.booking_count) for entry in manifest.businesses)
    visitors: int = sum(len(entry.visitors) for entry in manifest.businesses)
    return (
        f"Stored {len(manifest.businesses)} businesses with {messages} messages, "
        f"{bookings} bookings and {visitors} widget visitors (plus their demo "
        f"activity). Manifest: {path}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
