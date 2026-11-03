"""
The DPIA (docs/security/dpia.md) stays current and true (PRIV-04): its
review is less than a year old, every path it names exists, every risk
names the readiness checklist items its measures answer (ids that exist),
and it covers what the checklist asks a DPIA to cover, the no-show history
and profiling among them.
"""

import json
import re
from datetime import UTC, date, datetime, timedelta

from tests.legal.governance_documents import (
    REPOSITORY,
    missing_paths,
    read,
    section,
    table_rows,
)

DPIA: str = "docs/security/dpia.md"
CHECKLIST: str = "docs/security/readiness-checklist.json"
LONGEST_GAP: timedelta = timedelta(days=366)
CHECKLIST_ID: re.Pattern[str] = re.compile(r"\b[A-Z]+-[0-9]{2}\b")
# What PRIV-04 asks the assessment to cover, as the document words it.
COVERED: tuple[str, ...] = (
    "provvedimento n. 467",
    "call recordings",
    "transcripts",
    "Rebooking campaigns",
    "No-show history and profiling",
    "## Transfers",
    "Health details",
)


def checklist_ids() -> set[str]:
    items = json.loads((REPOSITORY / CHECKLIST).read_text(encoding="utf-8"))["items"]
    return {str(item["id"]) for item in items}


def test_the_dpia_was_reviewed_within_a_year() -> None:
    match = re.search(r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", read(DPIA), re.M)
    today = datetime.now(UTC).date()

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today, "a review cannot be dated ahead"
    assert today - reviewed <= LONGEST_GAP, "review the DPIA (at least yearly)"


def test_every_risk_maps_its_measures_to_checklist_items() -> None:
    rows = table_rows(section(read(DPIA), "Risks and measures"))
    known = checklist_ids()

    assert len(rows) >= 12
    for row in rows:
        assert len(row) == 5 and all(row), row
        cited = set(CHECKLIST_ID.findall(row[3]))
        assert cited, f"name the checklist items of: {row[0]}"
        assert sorted(cited - known) == [], row[0]


def test_the_dpia_covers_what_the_checklist_asks() -> None:
    text = read(DPIA)

    assert [topic for topic in COVERED if topic not in text] == []
    profiling = section(text, "No-show history and profiling")
    assert "no per-customer no-show list, score, ranking or automated" in profiling
    assert "`app/use_cases/campaigns/campaign_targets.py`" in profiling


def test_the_dpia_names_only_paths_that_exist() -> None:
    assert missing_paths(read(DPIA)) == []
