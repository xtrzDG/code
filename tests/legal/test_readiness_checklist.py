"""
The readiness checklist's status page (docs/security/readiness-checklist.md)
stays in step with the checklist itself (readiness-checklist.json): every
item has exactly one row with a known status, no row names an item the
checklist lacks, the counts in its summary line add up to its rows, and it
was verified within the last quarter.
"""

import json
import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
CHECKLIST: Path = ROOT / "docs" / "security" / "readiness-checklist.json"
STATUS_PAGE: Path = ROOT / "docs" / "security" / "readiness-checklist.md"
STATUSES: dict[str, str] = {
    "Done": "done",
    "Partial": "partial",
    "Gap": "gap",
    "Owner action": "owner action",
    "Not applicable": "not applicable",
}
ROW: re.Pattern[str] = re.compile(
    r"^\| ([A-Z]+-\d{2}) \| .+? \| (must|should|could) \| ([^|]+) \|", re.M
)
VERIFIED: re.Pattern[str] = re.compile(
    r"^Verified against the code on (\d{4}-\d{2}-\d{2}): (.+) \(of (\d+)\)\.$", re.M
)
REVIEW_PERIOD: timedelta = timedelta(days=92)


def checklist_ids() -> list[str]:
    items: list[dict[str, str]] = json.loads(CHECKLIST.read_text(encoding="utf-8"))[
        "items"
    ]
    return [item["id"] for item in items]


def rows() -> list[tuple[str, str]]:
    return [
        (match[1], match[3].strip())
        for match in ROW.finditer(STATUS_PAGE.read_text(encoding="utf-8"))
    ]


def test_every_item_has_one_row_with_a_known_status() -> None:
    found: list[tuple[str, str]] = rows()
    counts: Counter[str] = Counter(item_id for item_id, _ in found)

    assert sorted(counts) == sorted(checklist_ids())
    assert {item_id for item_id, seen in counts.items() if seen > 1} == set()
    assert {status for _, status in found} <= set(STATUSES)


def test_the_summary_line_adds_up_to_the_rows() -> None:
    match = VERIFIED.search(STATUS_PAGE.read_text(encoding="utf-8"))
    assert match is not None, "the page names the day it was verified"
    stated: dict[str, int] = {}
    for part in match[2].split(", "):
        label, _, number = part.rpartition(" ")
        stated[label] = int(number)
    counted: Counter[str] = Counter(STATUSES[status] for _, status in rows())

    assert int(match[3]) == len(checklist_ids())
    assert stated == {label: counted.get(label, 0) for label in STATUSES.values()}


def test_it_was_verified_within_the_last_quarter() -> None:
    match = VERIFIED.search(STATUS_PAGE.read_text(encoding="utf-8"))
    assert match is not None
    verified_on: date = date.fromisoformat(match[1])

    assert datetime.now(UTC).date() - verified_on <= REVIEW_PERIOD, (
        "Re-verify the checklist against the code and regenerate readiness-checklist.md"
    )
