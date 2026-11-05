"""
The accessibility statement (/[locale]/accessibility, ACC-02) is reviewed
yearly like security.txt is renewed: its date
(ACCESSIBILITY_STATEMENT_DATE in web/src/app/_landing/legal/accessibilityStatement.ts)
is never ahead and never more than a year old, every known limitation
offers an alternative in both languages, and businesses have ready text
for their own terms in both help languages.
"""

import re
from datetime import UTC, date, datetime, timedelta

from tests.legal.governance_documents import REPOSITORY, read

STATEMENT: str = "web/src/app/_landing/legal/accessibilityStatement.ts"
TEXTS: str = "web/src/i18n/messages/sections/site/accessibility.{language}.ts"
STATEMENT_DATE: re.Pattern[str] = re.compile(
    r'ACCESSIBILITY_STATEMENT_DATE = "([0-9]{4}-[0-9]{2}-[0-9]{2})"'
)
LIMITATION: re.Pattern[str] = re.compile(r'^    (\w+):\n      "([^"]+)",$', re.M)
LONGEST_GAP: timedelta = timedelta(days=366)
LIMITATIONS: tuple[str, ...] = ("legalLanguage", "userContent", "thirdParty", "audit")


def test_the_statement_was_reviewed_within_a_year() -> None:
    match = STATEMENT_DATE.search(read(STATEMENT))
    today = datetime.now(UTC).date()

    assert match is not None, "accessibilityStatement.ts lost its date"
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today, "a review cannot be dated ahead"
    assert today - reviewed <= LONGEST_GAP, (
        "review the accessibility statement and set ACCESSIBILITY_STATEMENT_DATE "
        "(AgID's model: at least once a year)"
    )


def test_every_known_limitation_offers_an_alternative_in_both_languages() -> None:
    for language in ("en", "it"):
        found = dict(LIMITATION.findall(read(TEXTS.format(language=language))))
        for key in LIMITATIONS:
            sentences = [part for part in found[key].split(". ") if part.strip()]
            assert len(sentences) >= 2, (language, key, "say how to get it otherwise")


def test_businesses_have_ready_text_for_their_terms() -> None:
    for language in ("en", "it"):
        article = REPOSITORY / "docs" / "help" / language / "accessibility-statement.md"
        text = article.read_text(encoding="utf-8")
        assert "form.agid.gov.it" in text and "30" in text, language
