"""
The prepared security questionnaire (docs/security/security-questionnaire.md,
GOV-05) stays true: reviewed within six months, every answer cites evidence,
and every document or path it cites exists.
"""

import re
from datetime import UTC, date, datetime, timedelta

from tests.legal.governance_documents import missing_paths, read, table_rows

QUESTIONNAIRE: str = "docs/security/security-questionnaire.md"
LONGEST_GAP: timedelta = timedelta(days=184)


def test_the_answers_were_reviewed_within_six_months() -> None:
    text = read(QUESTIONNAIRE)
    match = re.search(r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", text, re.M)
    today = datetime.now(UTC).date()

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today and today - reviewed <= LONGEST_GAP


def test_every_answer_cites_its_evidence() -> None:
    rows = table_rows(read(QUESTIONNAIRE))
    numbers = [int(row[0]) for row in rows]

    assert numbers == list(range(1, len(rows) + 1))
    for row in rows:
        assert len(row) == 4 and all(row), row
        assert "`" in row[3] or row[3].startswith("DPA"), row


def test_the_questionnaire_cites_only_paths_that_exist() -> None:
    assert missing_paths(read(QUESTIONNAIRE)) == []
