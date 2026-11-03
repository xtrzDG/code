"""
The AI Act record (docs/security/ai-act-assessment.md, AIACT-03 and
AIACT-04) stays current and true: reviewed within a year, every path it
names exists, it answers every point of Article 5(1) and Article 50, the
pull request template sends AI changes to it, and no code under `app/`
analyses emotions, sentiment or biometric traits before the record and the
DPIA say so.
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

RECORD: str = "docs/security/ai-act-assessment.md"
LONGEST_GAP: timedelta = timedelta(days=366)
ARTICLE_5_POINTS: list[str] = [f"({letter})" for letter in "abcdefgh"]
ARTICLE_50_PARAGRAPHS: list[str] = ["50(1)", "50(2)", "50(3)", "50(4)"]
# Analysis the record rules out; code that names it needs the record first.
EXCLUDED_ANALYSIS: re.Pattern[str] = re.compile(
    r"\b(sentiment|emotions?|emotional|biometrics?|biometric_\w+)\b", re.IGNORECASE
)


def test_the_record_was_reviewed_within_a_year() -> None:
    match = re.search(r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", read(RECORD), re.M)
    today = datetime.now(UTC).date()

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today, "a review cannot be dated ahead"
    assert today - reviewed <= LONGEST_GAP, "review the AI Act record (yearly)"


def test_the_record_answers_article_5_and_article_50_point_by_point() -> None:
    text = read(RECORD)
    article_5 = [
        row[0] for row in table_rows(section(text, "Article 5: no prohibited practice"))
    ]
    article_50 = [
        row[0] for row in table_rows(section(text, "Article 50: transparency"))
    ]

    assert article_5 == ARTICLE_5_POINTS
    assert article_50 == ARTICLE_50_PARAGRAPHS
    assert "**provider**" in text and "**deployer**" in text
    assert "Annex III" in text and "2026/1744" in text
    assert "to be verified against the Official Journal" in text


def test_the_record_names_only_paths_that_exist() -> None:
    assert missing_paths(read(RECORD)) == []


def test_ai_changes_are_sent_to_the_record() -> None:
    template = read(".github/pull_request_template.md")

    assert f"`{RECORD}`" in template
    assert "**AI features:**" in template


def test_no_code_analyses_emotions_or_biometric_traits() -> None:
    named = sorted(
        str(path.relative_to(REPOSITORY))
        for path in (REPOSITORY / "app").rglob("*.py")
        if EXCLUDED_ANALYSIS.search(path.read_text(encoding="utf-8"))
    )

    assert named == [], (
        "emotion, sentiment or biometric analysis needs the AI Act record "
        f"({RECORD}, Art. 50(3)) and the DPIA updated first: {named}"
    )
