"""
Per-language confusion of a run: for each scenario language, what its
assistant replies read as (the language-identity criterion's detector), so
"Russian scenarios answered in Ukrainian 3 times" is one row of the report.
Languages are compared by their base ("pt-BR" is "pt"); "?" counts replies
that told too little to say.
"""

from collections import Counter
from collections.abc import Sequence

from pydantic import BaseModel, Field

from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import base_language_code
from scripts.eval_harness.run_results import ScenarioResult

UNDETERMINED: str = "?"


class LanguageConfusionRow(BaseModel):
    """One scenario language: its replies, what they read as, how many missed."""

    expected: str
    replies: int
    read_as: dict[str, int] = Field(default_factory=dict[str, int])
    mismatched: int


def summarize_language_confusion(
    scenarios: Sequence[ScenarioResult],
) -> list[LanguageConfusionRow]:
    """A row per scenario language, by language; read-as counts most first."""

    counts: dict[str, Counter[str]] = {}
    for scenario in scenarios:
        expected: str = base_language_code(LanguageTag(scenario.language))
        counter: Counter[str] = counts.setdefault(expected, Counter())
        for sample in scenario.samples:
            counter.update(read_base(language) for language in sample.reply_languages)

    return [
        LanguageConfusionRow(
            expected=expected,
            replies=sum(counter.values()),
            read_as=dict(counter.most_common()),
            mismatched=sum(
                count
                for language, count in counter.items()
                if language not in (expected, UNDETERMINED)
            ),
        )
        for expected, counter in sorted(counts.items())
        if counter
    ]


def read_base(language: str) -> str:
    if language == UNDETERMINED:
        return UNDETERMINED

    return base_language_code(LanguageTag(language))
