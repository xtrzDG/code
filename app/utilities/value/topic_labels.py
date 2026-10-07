"""
The languages a topic is labelled in and which label a cabinet reads.

The nightly grouping names every topic in each cabinet language (English,
Russian, Georgian, Hebrew and German, the languages owners read the
cabinet in) and in the owner's own language, so an English or Hebrew
cabinet never shows a Russian owner's labels. The catch-all of other
questions is no label at all: the cabinet names it from its own
dictionary. Its owner-language text here only fills the version 1 `label`
field the release before still reads (the Hebrew and German ones are
drafts waiting for a native speaker, like the rest of those languages).
"""

from collections.abc import Sequence

from app.schemas.constants.localization import CabinetLanguage
from app.schemas.constants.value import TopicKind
from app.schemas.domain.conversation_topics import (
    ConversationTopic,
    LocalizedTopicLabel,
)
from app.schemas.typings.insights.constrained_strings import TopicLabel
from app.schemas.typings.localization.constrained_strings import LanguageTag

ENGLISH: str = "en"
# The languages the cabinet is translated into, in the order labels are asked.
CABINET_LANGUAGES: tuple[str, ...] = tuple(
    language.value
    for language in (
        CabinetLanguage.ENGLISH,
        CabinetLanguage.RUSSIAN,
        CabinetLanguage.GEORGIAN,
        CabinetLanguage.HEBREW,
        CabinetLanguage.GERMAN,
    )
)
# The catch-all's text in the owner-language `label` field (version 1 readers).
OTHER_TOPIC_LABELS: dict[str, str] = {
    "en": "Other questions",
    "ru": "Другие вопросы",
    "ka": "სხვა კითხვები",
    "he": "שאלות אחרות",
    "de": "Andere Fragen",
    "uk": "Інші питання",
    "fr": "Autres questions",
    "es": "Otras preguntas",
    "tr": "Diğer sorular",
}
# Labels a grouping of version 1 gave its catch-all (read as OTHER).
CATCH_ALL_LABELS: frozenset[str] = frozenset(
    {
        *(label.casefold() for label in OTHER_TOPIC_LABELS.values()),
        "other",
        "others",
        "other topics",
        "прочее",
        "другое",
        "разное",
        "სხვა",
        "אחר",
        "שונות",
        "sonstiges",
        "andere",
    }
)


def base_language(language: LanguageTag | str | None) -> str:
    """The primary subtag, lower case ("pt-BR" -> "pt"); "" for none."""

    return "" if language is None else str(language).split("-")[0].lower()


def label_languages(owner_language: LanguageTag) -> list[str]:
    """The owner's language first, then the cabinet languages not yet named."""

    languages: list[str] = [base_language(owner_language)]
    languages.extend(
        language for language in CABINET_LANGUAGES if language not in languages
    )
    return languages


def other_topic_label(language: LanguageTag | str) -> TopicLabel:
    """The catch-all's text in a language (English for one without it here)."""

    base: str = base_language(language)
    return TopicLabel(OTHER_TOPIC_LABELS.get(base, OTHER_TOPIC_LABELS[ENGLISH]))


def is_catch_all_label(label: str) -> bool:
    return " ".join(label.split()).casefold() in CATCH_ALL_LABELS


def label_in(labels: Sequence[LocalizedTopicLabel], language: str) -> TopicLabel | None:
    """The label of a base language, if the topic has one."""

    return next(
        (item.label for item in labels if base_language(item.language) == language),
        None,
    )


def resolve_topic_label(
    topic: ConversationTopic,
    language: LanguageTag,
    owner_language: LanguageTag,
) -> TopicLabel:
    """
    A topic's label for a reader of `language`: in that language, else in
    English (more readers read it than the owner's language), else in the
    owner's, else the version 1 label; the catch-all always in `language`.
    """

    if topic.kind is TopicKind.OTHER:
        return other_topic_label(language)

    for candidate in (
        base_language(language),
        ENGLISH,
        base_language(owner_language),
    ):
        found: TopicLabel | None = label_in(topic.labels, candidate)
        if found is not None:
            return found

    return topic.label
