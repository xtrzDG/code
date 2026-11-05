"""Every change of the API description is recorded in docs/API_CHANGELOG.md.

The newest entry names the committed `web/openapi.json` by its fingerprint,
so a pull request that changes the API without telling its clients fails.
Policy: docs/api-versioning.md.
"""

import hashlib
import re
from datetime import date
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
API_DESCRIPTION: Path = PROJECT_ROOT / "web" / "openapi.json"
CHANGELOG: Path = PROJECT_ROOT / "docs" / "API_CHANGELOG.md"
FINGERPRINT_LENGTH: int = 16
SPEC_LINE_PATTERN: re.Pattern[str] = re.compile(
    r"^Spec: `(?P<fingerprint>[0-9a-f]+)`$", re.MULTILINE
)
ENTRY_HEADING_PATTERN: re.Pattern[str] = re.compile(
    r"^## (?P<day>\d{4}-\d{2}-\d{2})\b", re.MULTILINE
)


def description_fingerprint(path: Path) -> str:
    """First hex digits of the SHA-256, as `sha256sum | cut -c1-16` prints."""

    return hashlib.sha256(path.read_bytes()).hexdigest()[:FINGERPRINT_LENGTH]


def test_newest_entry_names_the_committed_api_description() -> None:
    fingerprints: list[str] = SPEC_LINE_PATTERN.findall(
        CHANGELOG.read_text(encoding="utf-8")
    )
    expected: str = description_fingerprint(API_DESCRIPTION)

    assert fingerprints != [], "docs/API_CHANGELOG.md has no `Spec:` line."
    assert fingerprints[0] == expected, (
        "web/openapi.json changed: add an entry on top of docs/API_CHANGELOG.md "
        f"that says what changed for clients, with the line\n\nSpec: `{expected}`"
    )


def test_every_entry_names_one_description_and_entries_are_newest_first() -> None:
    text: str = CHANGELOG.read_text(encoding="utf-8")
    days: list[date] = [
        date.fromisoformat(day) for day in ENTRY_HEADING_PATTERN.findall(text)
    ]
    fingerprints: list[str] = SPEC_LINE_PATTERN.findall(text)

    assert days != []
    assert days == sorted(days, reverse=True)
    assert len(fingerprints) == len(days)
    assert all(len(value) == FINGERPRINT_LENGTH for value in fingerprints)
    assert len(set(fingerprints)) == len(fingerprints)
