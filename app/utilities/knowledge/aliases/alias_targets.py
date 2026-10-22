"""
Which languages a knowledge item still needs an alias in, and how the
model's suggestions join the item without overwriting the owner's work.
"""

from collections.abc import Sequence

from app.contracts.localization_utilities import LanguageDetectorContract
from app.schemas.constants.knowledge import KnowledgeAliasStatus
from app.schemas.domain.knowledge import KnowledgeAlias, KnowledgeItemDocument
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.aliases.alias_rules import has_alias_in
from app.utilities.knowledge.search_text import fold_words


def item_languages(
    item: KnowledgeItemDocument,
    candidates: Sequence[LanguageTag],
    default_language: LanguageTag,
    language_detector: LanguageDetectorContract,
) -> list[LanguageTag]:
    """
    The languages the item is written in: those it names among the
    candidates, or else the language its title is written in (detected
    among the candidates, the default language when unsure).
    """

    named: list[LanguageTag] = [
        language for language in item.languages if language in candidates
    ]
    return named or [
        language_detector.detect(str(item.title), list(candidates), default_language)
    ]


def missing_alias_languages(
    item: KnowledgeItemDocument,
    business_languages: Sequence[LanguageTag],
    own_languages: Sequence[LanguageTag],
) -> list[LanguageTag]:
    """The business's languages the item is neither written nor aliased in."""

    return [
        language
        for language in business_languages
        if language not in own_languages and not has_alias_in(item, language)
    ]


def add_suggested_aliases(
    item: KnowledgeItemDocument,
    suggestions: Sequence[tuple[LanguageTag, KnowledgeAliasText]],
    asked_title: KnowledgeTitle,
) -> KnowledgeItemDocument | None:
    """
    The item as stored now with the model's suggestions for languages that
    still have no alias (the first suggestion of each language); None,
    nothing to write, when the title changed since the model was asked
    (the suggestions translate a title that is gone) or every suggested
    language got an alias meanwhile.
    """

    if fold_words(item.title) != fold_words(asked_title):
        return None

    added: list[KnowledgeAlias] = []
    for language, text in suggestions:
        if has_alias_in(item, language) or any(
            alias.language == language for alias in added
        ):
            continue

        added.append(
            KnowledgeAlias(
                language=language,
                text=text,
                status=KnowledgeAliasStatus.SUGGESTED,
            )
        )

    if added == []:
        return None

    return item.model_copy(update={"aliases": [*item.aliases, *added]})
