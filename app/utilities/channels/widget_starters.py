"""
Starter questions of the website chat: one-tap chips before the visitor
writes, taken from the business's FAQ in the owner's order (the first
questions are the ones the owner put first), at most three per language.
"""

from collections.abc import Sequence

from app.contracts.localization_utilities import LanguageDetectorContract
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.channels.widget import WidgetStarterQuestionView
from app.schemas.typings.channels.strings import WidgetStarterQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag

STARTER_QUESTIONS_PER_LANGUAGE: int = 3
# A chip holds a short question; a longer title is an answer, not a chip.
MAX_STARTER_QUESTION_LENGTH: int = 80


def is_starter_candidate(item: KnowledgeItemDocument) -> bool:
    """An active, confirmed FAQ item whose question fits on a chip."""

    title: str = str(item.title).strip()
    return (
        item.kind is KnowledgeItemKind.FAQ
        and item.is_active
        and item.import_batch_id is None
        and 0 < len(title) <= MAX_STARTER_QUESTION_LENGTH
    )


def build_starter_questions(
    items: Sequence[KnowledgeItemDocument],
    languages: Sequence[LanguageTag],
    default_language: LanguageTag,
    language_detector: LanguageDetectorContract,
) -> list[WidgetStarterQuestionView]:
    """
    Up to three questions per customer language, in the owner's order. A
    question is in the languages its FAQ item names; one that names none
    is in the language it is written in (detected among the business's
    languages, the default language when unsure).
    """

    candidates: list[LanguageTag] = list(languages)
    counts: dict[str, int] = {}
    starters: list[WidgetStarterQuestionView] = []
    for item in items:
        if not is_starter_candidate(item):
            continue

        question: str = str(item.title).strip()
        item_languages: list[LanguageTag] = [
            language for language in item.languages if language in candidates
        ] or [language_detector.detect(question, candidates, default_language)]
        for language in item_languages:
            if counts.get(str(language), 0) >= STARTER_QUESTIONS_PER_LANGUAGE:
                continue

            counts[str(language)] = counts.get(str(language), 0) + 1
            starters.append(
                WidgetStarterQuestionView(
                    language=language,
                    text=WidgetStarterQuestionText(question),
                )
            )

    return starters
