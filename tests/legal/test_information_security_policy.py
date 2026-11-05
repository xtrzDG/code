"""
The information security policy (docs/security/information-security-policy.md,
GOV-05) stays in force: reviewed within a year, every document and path it
delegates to exists, it names its security owner, and every acknowledgment
names a person, the version read and how it was confirmed.
"""

import re
from datetime import UTC, date, datetime, timedelta

from tests.legal.governance_documents import missing_paths, read, section, table_rows

POLICY: str = "docs/security/information-security-policy.md"
LONGEST_GAP: timedelta = timedelta(days=366)


def test_the_policy_was_reviewed_within_a_year() -> None:
    text = read(POLICY)
    match = re.search(r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", text, re.M)
    today = datetime.now(UTC).date()

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today and today - reviewed <= LONGEST_GAP
    assert re.search(r"^Version [0-9]+, ", text, re.M)
    assert "**security owner**" in text


def test_every_acknowledgment_names_the_person_and_the_version() -> None:
    rows = table_rows(section(read(POLICY), "Acknowledgments"))
    version = re.search(r"^Version ([0-9]+), ", read(POLICY), re.M)

    assert rows and version is not None
    for row in rows:
        assert len(row) == 5 and all(row), row
        assert row[2].isdigit() and int(row[2]) <= int(version.group(1)), row


def test_the_policy_names_only_paths_that_exist() -> None:
    assert missing_paths(read(POLICY)) == []
