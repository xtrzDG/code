"""
Rules for the aliases of a knowledge item: the title in the business's
other languages (and synonyms customers use), searched like the title.

- an alias is in one of the business's languages, at most
  `MAX_ALIASES_PER_LANGUAGE` per language, stripped of surrounding spaces;
- the same text twice in a language (ignoring case, accents and spacing)
  is kept once, approved over suggested;
- a new title keeps the owner's approved aliases but drops the model's
  suggestions, which translated the old title.
"""

from collections.abc import Sequence

from app.schemas.constants.knowledge import KnowledgeAliasStatus
from app.schemas.domain.knowledge import KnowledgeAlias, KnowledgeItemDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.search_text import fold_words

MAX_ALIASES_PER_LANGUAGE: int = 3


def check_aliases(
    aliases: Sequence[KnowledgeAlias],
    business_languages: Sequence[LanguageTag],
) -> list[KnowledgeAlias]:
    """
    The aliases to store, in the given order (see the module docstring).

    Raises:
        ValidationFailedError: an alias in a language the business does not
            use, or too many aliases in one language.
    """

    allowed: set[str] = {str(language) for language in business_languages}
    kept: list[KnowledgeAlias] = []
    for alias in aliases:
        if str(alias.language) not in allowed:
            raise ValidationFailedError(
                f"Alias language {alias.language} is not a language of the business."
            )

        stripped = KnowledgeAlias(
            language=alias.language,
            text=KnowledgeAliasText(alias.text.strip()),
            status=alias.status,
        )
        duplicate: int | None = find_same_alias(kept, stripped)
        if duplicate is None:
            kept.append(stripped)
        elif stripped.status is KnowledgeAliasStatus.APPROVED:
            kept[duplicate] = stripped

    for language in allowed:
        count: int = sum(1 for alias in kept if str(alias.language) == language)
        if count > MAX_ALIASES_PER_LANGUAGE:
            raise ValidationFailedError(
                f"At most {MAX_ALIASES_PER_LANGUAGE} aliases per language "
                f"({language} has {count})."
            )

    return kept


def find_same_alias(
    aliases: Sequence[KnowledgeAlias], candidate: KnowledgeAlias
) -> int | None:
    """Position of an alias with the same language and folded text."""

    folded: str = fold_words(candidate.text)
    for position, alias in enumerate(aliases):
        if alias.language == candidate.language and fold_words(alias.text) == folded:
            return position

    return None


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
