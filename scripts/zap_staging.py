"""
The weekly active ZAP scan of staging (.github/workflows/zap-staging.yml):
the API definition it attacks and the proof that it was signed in.

    uv run --no-project python -m scripts.zap_staging definition \\
        web/openapi.json --server "$STAGING_URL" > zap/api-definition.json
    uv run --no-project python -m scripts.zap_staging signed-in \\
        --summary "$GITHUB_STEP_SUMMARY" zap/api-statuses.json

- definition: every operation of the public API (`/v1/public-api/...`, the
  routes an API key opens: reads and writes) from the committed
  web/openapi.json, without event streams, with staging as the only
  server. The scan signs in with an API key of staging's scan business.
- signed-in: from the answers scripts/zap_status_hook.py recorded, at
  least one public API answer was 2xx and fewer than half were 401; a scan
  whose key never reached the API would pass on refusals alone.

Exit codes: 0 done (signed in), 1 not signed in, 2 an input that cannot be
used (the scan proves nothing).
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

EXIT_DONE: int = 0
EXIT_NOT_SIGNED_IN: int = 1
EXIT_UNUSABLE: int = 2
PUBLIC_API: str = "/v1/public-api/"
STREAM_MEDIA_TYPE: str = "text/event-stream"
METHODS: frozenset[str] = frozenset({"get", "post", "put", "patch", "delete"})
UNAUTHENTICATED: int = 401


class ScanInputError(ValueError):
    """An input the scan cannot use."""


def is_stream(operation: dict[str, Any]) -> bool:
    responses = cast(dict[str, dict[str, Any]], operation.get("responses", {}))
    return any(
        STREAM_MEDIA_TYPE in each.get("content", {}) for each in responses.values()
    )


def public_api_definition(definition: dict[str, Any], server: str) -> dict[str, Any]:
    """The public API's operations of `definition`, for ZAP's OpenAPI import."""

    if urlsplit(server).scheme != "https" or not urlsplit(server).hostname:
        raise ScanInputError(f"{server!r}: staging's address must be https")
    paths: dict[str, Any] = {}
    for path, item in cast(dict[str, dict[str, Any]], definition["paths"]).items():
        if not path.startswith(PUBLIC_API):
            continue
        kept = {
            key: value
            for key, value in item.items()
            if key not in METHODS or not is_stream(cast(dict[str, Any], value))
        }
        if METHODS & set(kept):
            paths[path] = kept
    if not paths:
        raise ScanInputError("the definition has no public API operation")
    return {
        "openapi": definition["openapi"],
        "info": definition["info"],
        "servers": [{"url": server.rstrip("/")}],
        "paths": paths,
        "components": definition.get("components", {}),
    }


def read_statuses(path: Path) -> list[tuple[str, int]]:
    try:
        records: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScanInputError(f"{path}: unreadable ({error})") from error
    if not isinstance(records, list) or not records:
        raise ScanInputError(f"{path}: no answer recorded")
    statuses: list[tuple[str, int]] = []
    for record in cast(list[object], records):
        answer = cast(dict[str, object], record) if isinstance(record, dict) else {}
        url, status = answer.get("url"), answer.get("status")
        if not isinstance(url, str) or not isinstance(status, int):
            raise ScanInputError(f"{path}: {record!r} is not an answer")
        statuses.append((url, status))
    return statuses


def signed_in(statuses: Sequence[tuple[str, int]]) -> tuple[bool, str]:
    public = [
        status for url, status in statuses if urlsplit(url).path.startswith(PUBLIC_API)
    ]
    successes = sum(1 for status in public if 200 <= status < 300)
    refused = sum(1 for status in public if status == UNAUTHENTICATED)
    described = (
        f"{len(public)} answers of the public API: {successes} 2xx, {refused} 401"
    )
    return successes > 0 and 2 * refused < len(public), described


def definition_command(parsed: argparse.Namespace) -> int:
    try:
        source = cast(dict[str, Any], json.loads(parsed.openapi.read_text("utf-8")))
        cut = public_api_definition(source, parsed.server)
    except (OSError, ValueError, KeyError) as error:
        print(f"::error::Staging scan definition: {error}", file=sys.stderr)
        return EXIT_UNUSABLE
    json.dump(cut, sys.stdout, indent=1)
    return EXIT_DONE


def signed_in_command(parsed: argparse.Namespace) -> int:
    try:
        passed, described = signed_in(read_statuses(parsed.statuses))
    except ScanInputError as error:
        print(f"::error::{error}: the staging scan proves nothing.", file=sys.stderr)
        return EXIT_UNUSABLE
    if passed:
        line = f"The staging scan was signed in ({described})."
        print(line)
    else:
        line = (
            f"The staging scan was not signed in ({described}): check the"
            " secret STAGING_SCAN_API_KEY (an API key of staging's scan business)."
        )
        print(f"::error::{line}", file=sys.stderr)
    if parsed.summary is not None:
        with parsed.summary.open("a", encoding="utf-8") as summary:
            summary.write(f"\n{line}\n")
    return EXIT_DONE if passed else EXIT_NOT_SIGNED_IN


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scripts.zap_staging")
    commands = parser.add_subparsers(dest="command", required=True)
    definition = commands.add_parser("definition", help="the public API to attack")
    definition.add_argument("openapi", type=Path)
    definition.add_argument("--server", required=True)
    statuses = commands.add_parser("signed-in", help="was the scan signed in?")
    statuses.add_argument("statuses", type=Path)
    statuses.add_argument("--summary", type=Path)
    parsed = parser.parse_args(arguments)
    if parsed.command == "definition":
        return definition_command(parsed)
    return signed_in_command(parsed)


if __name__ == "__main__":
    sys.exit(main())
