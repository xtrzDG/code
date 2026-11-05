"""
The risk register (docs/security/risk-register.md, GOV-05) stays a real
register: reviewed within a year, every risk scored as likelihood times
impact on the 1-5 scales, owned by a role, treated with controls whose
paths exist and mapped to readiness checklist items that exist, and the
categories the checklist names (AI, telephony fraud, payments, privacy)
each have risks.
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

REGISTER: str = "docs/security/risk-register.md"
LONGEST_GAP: timedelta = timedelta(days=366)
OWNERS: frozenset[str] = frozenset({"security owner", "privacy lead", "incident lead"})
REQUIRED_CATEGORIES: frozenset[str] = frozenset(
    {"AI", "telephony fraud", "payments", "privacy", "security", "availability"}
)
CHECKLIST_ID: re.Pattern[str] = re.compile(r"\b[A-Z]+-[0-9]{2}\b")


def risks() -> list[list[str]]:
    return table_rows(section(read(REGISTER), "Register"))


def test_the_register_was_reviewed_within_a_year() -> None:
    match = re.search(
        r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", read(REGISTER), re.M
    )
    today = datetime.now(UTC).date()

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today and today - reviewed <= LONGEST_GAP


def test_every_risk_is_scored_owned_and_treated() -> None:
    items = json.loads(
        (REPOSITORY / "docs" / "security" / "readiness-checklist.json").read_text(
            encoding="utf-8"
        )
    )["items"]
    known = {str(item["id"]) for item in items}
    ids = [row[0] for row in risks()]

    assert len(ids) == len(set(ids)) >= 15
    for row in risks():
        assert len(row) == 10 and all(row), row
        likelihood, impact, score = int(row[3]), int(row[4]), int(row[5])
        assert 1 <= likelihood <= 5 and 1 <= impact <= 5, row[0]
        assert score == likelihood * impact, row[0]
        assert row[6] in OWNERS, row[0]
        cited = set(CHECKLIST_ID.findall(row[8]))
        assert cited and cited <= known, row[0]


def test_every_category_the_checklist_names_has_risks() -> None:
    categories = {row[2] for row in risks()}

    assert sorted(REQUIRED_CATEGORIES - categories) == []


def test_the_register_names_only_paths_that_exist() -> None:
    assert missing_paths(read(REGISTER)) == []
