"""
The team's AI literacy and security training (docs/security/ai-literacy.md,
GOV-06) stays complete and current: its five modules exist, the page is
reviewed yearly, a session is held or planned within a year, a planned one
that passed is recorded within a month, and the businesses' own guidance
is published in both help languages.
"""

import re
from datetime import UTC, date, datetime, timedelta

from tests.legal.governance_documents import (
    REPOSITORY,
    missing_paths,
    read,
    section,
    table_rows,
)

TRAINING: str = "docs/security/ai-literacy.md"
MODULES: tuple[str, ...] = (
    "### 1. What the assistant is and what it can do",
    "### 2. Its limits and when a person must step in",
    "### 3. Prompt injection and social engineering",
    "### 4. Data protection",
    "### 5. Incidents and who to call",
)
LONGEST_GAP: timedelta = timedelta(days=366)
OVERDUE_PLAN: timedelta = timedelta(days=31)
PLANNED: str = "(planned)"


def today() -> date:
    return datetime.now(UTC).date()


def test_every_module_exists_with_its_check() -> None:
    text = read(TRAINING)

    for module in MODULES:
        assert module in text, module
    assert text.count("*Check:*") == len(MODULES)


def test_the_training_page_was_reviewed_within_a_year() -> None:
    match = re.search(r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", read(TRAINING), re.M)

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today() and today() - reviewed <= LONGEST_GAP


def test_a_session_was_held_or_is_planned_within_a_year() -> None:
    rows = table_rows(section(read(TRAINING), "Records"))
    days = [(date.fromisoformat(row[3][:10]), PLANNED in row[3]) for row in rows]

    assert rows, "record the training or plan the next session"
    for row in rows:
        assert len(row) == 6 and row[0] and row[2] and row[4], row
    assert all(day <= today() for day, planned in days if not planned)
    assert all(today() - day <= OVERDUE_PLAN for day, planned in days if planned), (
        "a planned session has passed: record it, or plan it again"
    )
    assert any(abs(today() - day) <= LONGEST_GAP for day, _ in days)


def test_the_businesses_guidance_is_published_in_both_languages() -> None:
    for language in ("en", "it"):
        assert (REPOSITORY / "docs" / "help" / language / "ai-use-guidance.md").is_file()
    assert "ai-literacy.md" in read("docs/operations/offboarding.md")


def test_the_training_names_only_paths_that_exist() -> None:
    assert missing_paths(read(TRAINING)) == []
