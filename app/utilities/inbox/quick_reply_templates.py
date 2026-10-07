"""
Saved-reply texts: their variables in braces, choosing the variant for a
conversation's language, and filling the variables in.

A variable is a word in braces ({name}); other braces stay text, so a
reply may still say "{" or "{ }". Filling never invents a value: a
variable without one stays in braces for staff to complete.
"""

import re
from collections.abc import Mapping, Sequence

from app.schemas.constants.inbox import QuickReplyVariable
from app.schemas.domain.quick_replies import QuickReplyVariant
from app.schemas.typings.localization.constrained_strings import LanguageTag

PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
KNOWN_NAMES: frozenset[str] = frozenset(
    variable.value for variable in QuickReplyVariable
)


def placeholder_names(text: str) -> list[str]:
    """The words in braces of a text, each once, in order of appearance."""

    return list(dict.fromkeys(PLACEHOLDER_PATTERN.findall(text)))


def unknown_placeholders(texts: Sequence[str]) -> list[str]:
    """Words in braces that are not variables the inbox fills."""

    return [
        name
        for name in dict.fromkeys(
            name for text in texts for name in placeholder_names(text)
        )
        if name not in KNOWN_NAMES
    ]


def variables_in(texts: Sequence[str]) -> list[QuickReplyVariable]:
    """The variables the texts use, each once, in order of appearance."""

    return [
        QuickReplyVariable(name)
        for name in dict.fromkeys(
            name for text in texts for name in placeholder_names(text)
        )
        if name in KNOWN_NAMES
    ]


def base_language(language: LanguageTag) -> str:
    return str(language).split("-")[0].lower()


def choose_variant(
    variants: Sequence[QuickReplyVariant],
    language: LanguageTag | None,
    fallback_language: LanguageTag,
) -> QuickReplyVariant:
    """
    The variant of the conversation's language, else of its base language
    ("pt" for "pt-BR"), else of the business's default language (the same
    way), else the first one. `variants` is never empty.
    """

    for wanted in (language, fallback_language):
        if wanted is None:
            continue

        for variant in variants:
            if str(variant.language).lower() == str(wanted).lower():
                return variant

        for variant in variants:
            if base_language(variant.language) == base_language(wanted):
                return variant

    return variants[0]


def fill_variables(
    text: str,
    values: Mapping[QuickReplyVariable, str],
) -> tuple[str, list[QuickReplyVariable]]:
    """
    The text with every variable that has a value filled in, and the
    variables left in braces because they have none.
    """

    missing: list[QuickReplyVariable] = []

    def replace(match: re.Match[str]) -> str:
        name: str = match.group(1)
        if name not in KNOWN_NAMES:
            return match.group(0)

        variable = QuickReplyVariable(name)
        value: str | None = values.get(variable)
        if value is None:
            if variable not in missing:
                missing.append(variable)

            return match.group(0)

        return value

    return PLACEHOLDER_PATTERN.sub(replace, text), missing
