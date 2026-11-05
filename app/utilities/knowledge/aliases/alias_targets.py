"""
Which languages a knowledge item still needs an alias in, and how the
model's suggestions join the item without overwriting the owner's work.
"""

from collections.abc import Sequence

from app.contracts.localization_utilities import LanguageDetectorContract
from app.schemas.constants.knowledge import KnowledgeAliasStatus
from app.schemas.domain.knowledge import (
    KnowledgeAlias,
    KnowledgeAliasRequest,
    KnowledgeItemDocument,
)
from app.schemas.dto.language_detection import DetectedLanguage
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.aliases.alias_rules import has_alias_in
from app.utilities.knowledge.search_text import fold_words

# "Undetermined" (BCP 47): the title is in none of the candidate languages.
UNKNOWN_LANGUAGE: LanguageTag = LanguageTag("und")


def item_languages(
    item: KnowledgeItemDocument,
    candidates: Sequence[LanguageTag],
    default_language: LanguageTag,
    language_detector: LanguageDetectorContract,
) -> list[LanguageTag]:
    """
    The languages the item is written in: those it names among the
    candidates, or else the language its title is written in. The title is
    read among the candidates first; a title in none of them (an English
    menu of a Georgian and Russian business) is read among every language,
    so the business's own languages are all asked for. Only a title that
    tells nothing counts as the default language.
    """

    named: list[LanguageTag] = [
        language for language in item.languages if language in candidates
    ]
    if named:
        return named

    among_candidates: LanguageTag = language_detector.detect(
        str(item.title), list(candidates), UNKNOWN_LANGUAGE
    )
    if among_candidates != UNKNOWN_LANGUAGE:
        return [among_candidates]

    detected: DetectedLanguage = language_detector.detect_any(
        MessageText(str(item.title)), list(candidates), default_language, None, None
    )
    return [detected.language if detected.is_read_from_text else default_language]


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


def asked_alias_languages(item: KnowledgeItemDocument) -> list[LanguageTag]:
    """
    The languages the model was already asked to name the item in under
    its current title (ignoring case, accents and spacing); none after a
    new title.
    """

    request: KnowledgeAliasRequest | None = item.alias_request
    if request is None or fold_words(request.title) != fold_words(item.title):
        return []

    return list(request.languages)


def record_alias_request(
    item: KnowledgeItemDocument,
    asked_title: KnowledgeTitle,
    languages: Sequence[LanguageTag],
) -> KnowledgeItemDocument:
    """
    The item remembering that the model was asked for `languages` under
    `asked_title` (added to what was asked under the same title before).
    """

    earlier: list[LanguageTag] = asked_alias_languages(item)
    return item.model_copy(
        update={
            "alias_request": KnowledgeAliasRequest(
                title=asked_title,
                languages=[
                    *earlier,
                    *(language for language in languages if language not in earlier),
                ],
            )
        }
    )
