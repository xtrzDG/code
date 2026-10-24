"""
Proves that ZAP's /v1 baseline (.github/workflows/zap.yml) scanned the API
signed in as the seeded owner, from the answers scripts/zap_status_hook.py
recorded:

    uv run --no-project python -m scripts.zap_auth_check \\
        --summary "$GITHUB_STEP_SUMMARY" zap/api-statuses.json

Only the seeded business's routes (`/v1/businesses/...`) count: with the
owner's token they answer 2xx (or 4xx for a made-up nested id), never 401
but for the few that ask for a fresh sign-in; without it every one of them
answers 401. The check fails unless at least one of them answered 2xx and
fewer than half answered 401. Exit codes: 0 signed in, 1 not signed in,
2 a missing, empty or unreadable status file (the scan proves nothing).
"""

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

EXIT_SIGNED_IN: int = 0
EXIT_NOT_SIGNED_IN: int = 1
EXIT_UNUSABLE: int = 2
BUSINESS_ROUTES: str = "/v1/businesses/"
UNAUTHENTICATED: int = 401


class StatusFileError(ValueError):
    """The status file cannot be used."""


@dataclass(frozen=True)
class Tally:
    answers: int
    successes: int
    unauthenticated: int

    @property
    def signed_in(self) -> bool:
        return self.successes > 0 and 2 * self.unauthenticated < self.answers

    def describe(self) -> str:
        return (
            f"{self.answers} answers of the seeded business's routes: "
            f"{self.successes} 2xx, {self.unauthenticated} 401"
        )


def read_statuses(path: Path) -> list[tuple[str, int]]:
    try:
        records: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise StatusFileError(f"{path}: unreadable ({error})") from error
    if not isinstance(records, list) or not records:
        raise StatusFileError(f"{path}: no answer recorded")
    statuses: list[tuple[str, int]] = []
    for record in cast(list[object], records):
        if not isinstance(record, dict):
            raise StatusFileError(f"{path}: {record!r} is not an answer")
        answer = cast(dict[str, object], record)
        url, status = answer.get("url"), answer.get("status")
        if not isinstance(url, str) or not isinstance(status, int):
            raise StatusFileError(f"{path}: {record!r} is not an answer")
        statuses.append((url, status))
    return statuses


def tally(statuses: Sequence[tuple[str, int]]) -> Tally:
    business = [
        status
        for url, status in statuses
        if urlsplit(url).path.startswith(BUSINESS_ROUTES)
    ]
    return Tally(
        answers=len(business),
        successes=sum(1 for status in business if 200 <= status < 300),
        unauthenticated=sum(1 for status in business if status == UNAUTHENTICATED),
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.zap_auth_check",
        description="Was ZAP's /v1 baseline signed in as the seeded owner?",
    )
    parser.add_argument("statuses", type=Path, help="the hook's api-statuses.json")
    parser.add_argument("--summary", type=Path, help="Markdown summary to append to")
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parsed: argparse.Namespace = build_argument_parser().parse_args(arguments)
    try:
        result = tally(read_statuses(parsed.statuses))
    except StatusFileError as error:
        print(f"::error::{error}: the /v1 scan proves nothing.", file=sys.stderr)
        return EXIT_UNUSABLE

    if result.signed_in:
        line = f"The /v1 scan was signed in ({result.describe()})."
        print(line)
        code = EXIT_SIGNED_IN
    else:
        line = (
            f"The /v1 scan was not signed in ({result.describe()}): "
            "its findings cover the sign-in refusal only."
        )
        print(f"::error::{line}", file=sys.stderr)
        code = EXIT_NOT_SIGNED_IN
    if parsed.summary is not None:
        with parsed.summary.open("a", encoding="utf-8") as summary:
            summary.write(f"\n{line}\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
