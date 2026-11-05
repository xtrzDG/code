"""
Refresh the vendored provider specifications of the contract tests:

    uv run python -m scripts.refresh_vendor_specs                # every provider
    uv run python -m scripts.refresh_vendor_specs --only meta    # one provider
    uv run python -m scripts.refresh_vendor_specs --check        # drift only

Each provider's published document (OpenAPI, Google discovery, the types
of the vendor's SDK) is read, the schemas the platform exchanges with it
are kept, and `tests/contracts/specs/<file>.json` is rewritten. `--check`
writes nothing and exits with 1 when a vendor's schemas changed since the
files were refreshed: the nightly `contracts-live.yml` reports that as
provider drift. `--cache DIR` reads documents from DIR when they are there
and keeps the downloads there. Hand-written specs ("kind": "documented")
are not touched (tests/contracts/README.md).
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from scripts.vendor_specs.spec_documents import (
    VendorDocumentError,
    document_version,
    load_document,
)
from scripts.vendor_specs.spec_files import (
    build_spec_file,
    changed_definitions,
    read_spec_file,
    render,
    write_atomically,
)
from scripts.vendor_specs.spec_model import JsonObject, VendorSpec
from scripts.vendor_specs.spec_registry import GENERATED_SPECS

DEFAULT_SPECS_DIRECTORY: Path = (
    Path(__file__).resolve().parents[1] / "tests" / "contracts" / "specs"
)
DESCRIPTION: str = "Refresh the vendored provider specifications of the contract tests."
EXIT_OK: int = 0
EXIT_DRIFT: int = 1
EXIT_FAILED: int = 2


def parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="PROVIDER",
        choices=sorted({spec.provider for spec in GENERATED_SPECS}),
        help="refresh only this provider (repeatable)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit 1 when a vendor's schemas changed",
    )
    parser.add_argument("--cache", type=Path, default=None, metavar="DIR")
    parser.add_argument(
        "--specs", type=Path, default=DEFAULT_SPECS_DIRECTORY, metavar="DIR"
    )
    return parser.parse_args(list(arguments))


def refresh_spec(
    spec: VendorSpec,
    specs_directory: Path,
    cache_directory: Path | None,
    is_check: bool,
) -> list[str]:
    """The changed definitions of one file (written unless only checking)."""

    document: JsonObject = load_document(spec, cache_directory)
    fresh: JsonObject = build_spec_file(
        spec, document, document_version(spec, document)
    )
    path: Path = specs_directory / spec.file_name
    changed: list[str] = changed_definitions(read_spec_file(path), fresh)
    if not is_check:
        write_atomically(path, render(fresh))

    return changed


def main(arguments: Sequence[str]) -> int:
    options: argparse.Namespace = parse_arguments(arguments)
    selected: list[VendorSpec] = [
        spec
        for spec in GENERATED_SPECS
        if not options.only or spec.provider in options.only
    ]
    status: int = EXIT_OK
    for spec in selected:
        try:
            changed: list[str] = refresh_spec(
                spec, options.specs, options.cache, options.check
            )
        except (VendorDocumentError, ValueError) as error:
            print(f"{spec.file_name}: FAILED: {error}")
            status = EXIT_FAILED
            continue

        if not changed:
            print(f"{spec.file_name}: unchanged")
            continue

        print(f"{spec.file_name}: {len(changed)} changed: {', '.join(changed[:12])}")
        if options.check and status == EXIT_OK:
            status = EXIT_DRIFT

    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
