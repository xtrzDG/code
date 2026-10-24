"""
Rules for the aliases of a knowledge item: the title in the business's
other languages (and synonyms customers use), searched like the title.

- an alias is in one of the business's languages, at most
  `MAX_ALIASES_PER_LANGUAGE` per language, as written (the primitive
  already refuses surrounding spaces);
- the same text twice in a language (ignoring case, accents and spacing)
  is kept once, approved over suggested;
- a new title keeps the owner's approved aliases but drops the model's
  suggestions, which translated the old title.
"""

from collections.abc import Sequence

from app.schemas.constants.knowledge import (
    MAX_ALIASES_PER_LANGUAGE,
    KnowledgeAliasStatus,
)
from app.schemas.domain.knowledge import KnowledgeAlias, KnowledgeItemDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.search_text import fold_words


def check_aliases(
    aliases: Sequence[KnowledgeAlias],
    business_languages: Sequence[LanguageTag],
) -> list[KnowledgeAlias]:
    """
    The aliases to store, in the given order (see the module docstring).

    One pass: each alias is looked up by its language and folded text, and
    a language is refused as soon as it holds one alias too many, so a long
    list costs no more than reading it once.

    Raises:
        ValidationFailedError: an alias in a language the business does not
            use, or too many aliases in one language.
    """

    allowed: set[str] = {str(language) for language in business_languages}
    kept: dict[tuple[str, str], KnowledgeAlias] = {}
    per_language: dict[str, int] = {}
    for alias in aliases:
        language: str = str(alias.language)
        if language not in allowed:
            raise ValidationFailedError(
                f"Alias language {alias.language} is not a language of the business."
            )

        key: tuple[str, str] = (language, fold_words(alias.text))
        if key in kept:
            if alias.status is KnowledgeAliasStatus.APPROVED:
                kept[key] = alias
            continue

        per_language[language] = per_language.get(language, 0) + 1
        if per_language[language] > MAX_ALIASES_PER_LANGUAGE:
            raise ValidationFailedError(
                f"At most {MAX_ALIASES_PER_LANGUAGE} aliases per language "
                f"({language} has more)."
            )

        kept[key] = alias

    return list(kept.values())


def carry_aliases(
    existing: KnowledgeItemDocument, title: KnowledgeTitle
) -> list[KnowledgeAlias]:
    """
    The aliases an item keeps when its other fields change: all of them
    under the same title (ignoring case, accents and spacing), only the
    approved ones under a new title.
    """

    if fold_words(existing.title) == fold_words(title):
        return list(existing.aliases)

    return [
        alias
        for alias in existing.aliases
        if alias.status is KnowledgeAliasStatus.APPROVED
    ]


def approved_aliases_in(
    item: KnowledgeItemDocument, language: LanguageTag
) -> list[KnowledgeAlias]:
    """The owner's aliases of the item in `language`, in the owner's order."""

    return [
        alias
        for alias in item.aliases
        if alias.language == language and alias.status is KnowledgeAliasStatus.APPROVED
    ]


def has_alias_in(item: KnowledgeItemDocument, language: LanguageTag) -> bool:
    """Whether the item has any alias (suggested or approved) in `language`."""

    return any(alias.language == language for alias in item.aliases)
