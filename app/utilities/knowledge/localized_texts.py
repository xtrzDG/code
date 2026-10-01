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


def build_localized_rule_lines(
    en: Sequence[str],
    ru: Sequence[str],
    ka: Sequence[str] | None = None,
) -> LocalizedText:
    """
    Build a LocalizedText that holds one rule per line in every language.

    All languages must list the same rules in the same order.
    """

    if len(en) != len(ru) or (ka is not None and len(ka) != len(en)):
        raise ValueError("Every language must list the same number of rules.")

    return build_localized_text(
        en=RULE_LINE_SEPARATOR.join(en),
        ru=RULE_LINE_SEPARATOR.join(ru),
        ka=None if ka is None else RULE_LINE_SEPARATOR.join(ka),
    )


def split_rule_lines(text: LocalizedTextValue) -> list[str]:
    """Split a resolved rule text into its non-empty lines."""

    lines: list[str] = []
    for raw_line in text.split(RULE_LINE_SEPARATOR):
        line: str = raw_line.strip()
        if line != "":
            lines.append(line)

    return lines
