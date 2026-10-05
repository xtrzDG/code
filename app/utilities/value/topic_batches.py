"""
What one night's grouping sends the model: the first messages of the
conversations customers started and the open questions the assistant could
not answer, in one batch per customer language (the largest languages
first, the rest together under no language).
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.schemas.constants.value import TopicKind
from app.schemas.domain.conversation_topics import (
    ConversationTopic,
    LocalizedTopicLabel,
    TopicLanguageGroup,
)
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.insights.constrained_strings import TopicLabel
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.value.topic_answers import GroupedTopic
from app.utilities.value.topic_labels import label_in, other_topic_label

# Languages grouped one by one; a model call each.
MAX_TOPIC_LANGUAGES: int = 4


@dataclass(frozen=True)
class FirstMessage:
    """The language a conversation was in and what its customer wrote first."""

    language: LanguageTag | None
    text: str


@dataclass
class TopicBatch:
    """The items of one customer language (None: the others together)."""

    language: LanguageTag | None
    first_messages: list[str] = field(default_factory=list[str])
    open_questions: list[str] = field(default_factory=list[str])


def base_of(language: LanguageTag | None) -> str:
    return "" if language is None else str(language).split("-")[0].lower()


def language_batches(
    first_messages: Sequence[FirstMessage],
    open_questions: Sequence[UnansweredQuestionDocument],
) -> list[TopicBatch]:
    """
    One batch per language of the most conversations (at most
    MAX_TOPIC_LANGUAGES, ties by tag), then one for the rest; a question
    joins the batch of its base language. Empty batches are left out.
    """

    counts: Counter[str] = Counter(
        base_of(message.language) for message in first_messages if message.language
    )
    kept: list[str] = sorted(counts, key=lambda base: (-counts[base], base))[
        :MAX_TOPIC_LANGUAGES
    ]
    batches: dict[str, TopicBatch] = {
        base: TopicBatch(language=LanguageTag(base)) for base in kept
    }
    rest: TopicBatch = TopicBatch(language=None)

    def batch_of(language: LanguageTag | None) -> TopicBatch:
        return batches.get(base_of(language), rest)

    for message in first_messages:
        batch_of(message.language).first_messages.append(message.text)

    for question in open_questions:
        batch_of(question.language).open_questions.append(str(question.question))

    return [
        batch
        for batch in [*batches.values(), rest]
        if batch.first_messages or batch.open_questions
    ]


def previous_labels(
    groups: Sequence[TopicLanguageGroup],
    language: LanguageTag | None,
    owner_language: LanguageTag,
) -> list[TopicLabel]:
    """
    The owner-language labels the last grouping gave the named topics of
    the same customer language (offered again, so a topic keeps its name).
    """

    return [
        label_in(topic.labels, base_of(owner_language)) or topic.label
        for group in groups
        if base_of(group.language) == base_of(language)
        for topic in group.topics
        if topic.kind is TopicKind.NAMED
    ]


def to_group(
    batch: TopicBatch,
    topics: Sequence[GroupedTopic],
    owner_language: LanguageTag,
) -> TopicLanguageGroup:
    """
    The stored group: each topic's labels by language, and as its version 1
    `label` the owner-language one (else the first; the catch-all's text).
    """

    return TopicLanguageGroup(
        language=batch.language,
        conversation_count=PeriodItemCount(len(batch.first_messages)),
        topics=[
            ConversationTopic(
                label=(
                    other_topic_label(owner_language)
                    if topic.kind is TopicKind.OTHER
                    else dict(topic.labels).get(
                        base_of(owner_language), topic.labels[0][1]
                    )
                ),
                kind=topic.kind,
                labels=[
                    LocalizedTopicLabel(language=LanguageTag(language), label=label)
                    for language, label in topic.labels
                ],
                conversation_count=PeriodItemCount(topic.conversation_count),
                unanswered_count=PeriodItemCount(topic.question_count),
            )
            for topic in topics
        ],
    )
