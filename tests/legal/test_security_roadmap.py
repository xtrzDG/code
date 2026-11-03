"""
The security roadmap (docs/security/roadmap.md) stays honest: reviewed
within a year, every engineering item names checklist ids that exist and
its trigger and owner step, the certification path names SOC 2 and ISO
27001, and the items the checklist leaves to infrastructure or a person
(KMS envelope encryption, separate origins, an admin origin, independent
review, the contract set) are on it.
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

ROADMAP: str = "docs/security/roadmap.md"
LONGEST_GAP: timedelta = timedelta(days=366)
CHECKLIST_ID: re.Pattern[str] = re.compile(r"\b[A-Z]+-[0-9]{2}\b")
ROADMAP_ITEMS: frozenset[str] = frozenset(
    {"SEC-04", "WEB-07", "AUTHZ-04", "SDLC-05", "GOV-01"}
)


def test_the_roadmap_was_reviewed_within_a_year() -> None:
    match = re.search(r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", read(ROADMAP), re.M)
    today = datetime.now(UTC).date()

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today and today - reviewed <= LONGEST_GAP


def test_every_item_names_its_checklist_ids_trigger_and_owner_step() -> None:
    items = json.loads(
        (REPOSITORY / "docs" / "security" / "readiness-checklist.json").read_text(
            encoding="utf-8"
        )
    )["items"]
    known = {str(item["id"]) for item in items}
    rows = table_rows(section(read(ROADMAP), "Engineering roadmap"))
    cited = {found for row in rows for found in CHECKLIST_ID.findall(row[1])}

    for row in rows:
        assert len(row) == 6 and all(row), row
    assert cited <= known
    assert sorted(ROADMAP_ITEMS - cited) == []


def test_the_certification_path_names_both_standards() -> None:
    certification = section(read(ROADMAP), "Certification")

    assert "SOC 2 Type II" in certification and "ISO/IEC 27001" in certification


def test_the_roadmap_names_only_paths_that_exist() -> None:
    assert missing_paths(read(ROADMAP)) == []
