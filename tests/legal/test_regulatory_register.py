"""
The regulatory applicability register (docs/security/regulatory-register.md,
GOV-08) stays current: reviewed within a year, a row for every regime the
readiness checklist names (NIS2, the CRA, the EAA, the AI Act role, the DPO
need, the PCI role), each with its facts, decision, trigger and owner, and
only paths that exist.
"""

import re
from datetime import UTC, date, datetime, timedelta

from tests.legal.governance_documents import missing_paths, read, section, table_rows

REGISTER: str = "docs/security/regulatory-register.md"
LONGEST_GAP: timedelta = timedelta(days=366)
REQUIRED: tuple[str, ...] = (
    "NIS2",
    "Cyber Resilience Act",
    "European Accessibility Act",
    "AI Act",
    "data protection officer",
    "PCI DSS",
)


def test_the_register_was_reviewed_within_a_year() -> None:
    text = read(REGISTER)
    match = re.search(r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", text, re.M)
    today = datetime.now(UTC).date()

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today and today - reviewed <= LONGEST_GAP
    assert "D.Lgs. 138/2024" in text


def test_every_regime_of_the_checklist_has_a_complete_row() -> None:
    rows = table_rows(section(read(REGISTER), "Register"))
    regimes = " ".join(row[0] for row in rows)

    assert [name for name in REQUIRED if name not in regimes] == []
    for row in rows:
        assert len(row) == 6 and all(row), row


def test_the_register_names_only_paths_that_exist() -> None:
    assert missing_paths(read(REGISTER)) == []
