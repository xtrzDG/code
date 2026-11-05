"""
The restore test record stays current (REL-03): a full restore was held
within 92 days or one is planned within 92 days, a planned one that has
passed is recorded within a month, and a held one carries its achieved
RPO and RTO and its integrity checks.
"""

import re
from datetime import UTC, date, datetime, timedelta

from tests.legal.governance_documents import read, section, table_rows

REPORT: str = "docs/operations/restore-test-report.md"
LONGEST_GAP: timedelta = timedelta(days=92)
OVERDUE_PLAN: timedelta = timedelta(days=31)
PLANNED: str = "(planned)"
DURATION: re.Pattern[str] = re.compile(r"^[0-9]+:[0-5][0-9]$")


def today() -> date:
    return datetime.now(UTC).date()


def records() -> list[list[str]]:
    return table_rows(section(read(REPORT), "Record"))


def test_a_restore_test_was_held_or_is_planned_within_a_quarter() -> None:
    rows = [(date.fromisoformat(row[0][:10]), PLANNED in row[0]) for row in records()]
    held = [day for day, is_planned in rows if not is_planned]
    planned = [day for day, is_planned in rows if is_planned]

    assert rows, "record the restore test or plan the next one"
    assert all(day <= today() for day in held), "a held restore test lies ahead"
    assert all(today() - day <= OVERDUE_PLAN for day in planned), (
        "a planned restore test has passed: record it, or plan it again"
    )
    assert any(today() - day <= LONGEST_GAP for day in held) or any(
        day - today() <= LONGEST_GAP for day in planned
    )


def test_a_held_restore_test_records_its_measures() -> None:
    for row in records():
        if PLANNED in row[0]:
            continue
        assert len(row) == 8, row
        if "path B" in row[1]:
            assert DURATION.match(row[3]) and DURATION.match(row[4]), row
            assert "RLS" in row[5] and "recordings" in row[5], row
        assert row[7], "name who ran it"


def test_the_template_has_the_record_columns() -> None:
    template = table_rows(section(read(REPORT), "Template"))
    header = read(REPORT).split("## Record", 1)[1].splitlines()[2]

    assert len(template) == 1 and len(template[0]) == 8
    assert "RPO achieved" in header and "RTO achieved" in header
