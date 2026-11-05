"""Build and split localized texts of the niche catalog and owner-facing messages."""

from collections.abc import Sequence

from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue

# Every LocalizedText carries English, so English is the last-resort language
# when neither the caller nor the business names one.
FALLBACK_LANGUAGE_TAG: LanguageTag = LanguageTag("en")
RULE_LINE_SEPARATOR: str = "\n"


def build_localized_text(en: str, ru: str, ka: str | None = None) -> LocalizedText:
    """
    Build a LocalizedText from catalog literals.

    English and Russian are mandatory for owner-facing texts; Georgian is
    added where it is available and otherwise falls back to English.
    """

    values: dict[LanguageTag, LocalizedTextValue] = {
        LanguageTag("en"): LocalizedTextValue(en),
        LanguageTag("ru"): LocalizedTextValue(ru),
    }
    if ka is not None:
        values[LanguageTag("ka")] = LocalizedTextValue(ka)

    return LocalizedText(values=values)


def split_rule_lines(text: LocalizedTextValue) -> list[str]:
    """Split a resolved rule text into its non-empty lines."""

    lines: list[str] = []
    for raw_line in text.split(RULE_LINE_SEPARATOR):
        line: str = raw_line.strip()
        if line != "":
            lines.append(line)

    return lines


def join_rule_lines(
    lines: Sequence[LocalizedText],
    languages: Sequence[LanguageTag],
) -> LocalizedText:
    """
    The lines as one rule per line, in each of `languages` (in that order)
    that has every line: a list never mixes languages, so a language
    missing one line reads the English list.
    """

    return LocalizedText(
        values={
            language: LocalizedTextValue(
                RULE_LINE_SEPARATOR.join(str(line.values[language]) for line in lines)
            )
            for language in languages
            if all(language in line.values for line in lines)
        }
    )


def join_rule_lists(first: LocalizedText, second: LocalizedText) -> LocalizedText:
    """The rules of `first` followed by those of `second`, where both exist."""

    return LocalizedText(
        values={
            language: LocalizedTextValue(
                f"{value}{RULE_LINE_SEPARATOR}{second.values[language]}"
            )
            for language, value in first.values.items()
            if language in second.values
        }
    )
