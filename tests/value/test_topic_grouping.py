"""Reading the cheap model's topics, and what it is sent per language."""

import json

from typed_time_provider import Microseconds

from app.schemas.constants.value import TopicKind
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.value.topic_answers import (
    MAX_TOPICS,
    GroupedTopic,
    read_grouped_topics,
)
from app.utilities.value.topic_batches import (
    MAX_TOPIC_LANGUAGES,
    FirstMessage,
    language_batches,
)
from app.utilities.value.topic_grouping import (
    MAX_ITEM_CHARACTERS,
    mask_customer_text,
)

EN: list[str] = ["en"]


def answer(*topics: tuple[str, list[str]]) -> str:
    """A model that names each topic with one label (read as the first language's)."""

    body = {"topics": [{"label": label, "items": items} for label, items in topics]}
    return "Here you go:\n" + json.dumps(body, ensure_ascii=False)


def first_label(topic: GroupedTopic) -> str:
    return str(topic.labels[0][1])


def test_each_item_counts_once_and_unknown_ones_are_ignored() -> None:
    topics = read_grouped_topics(
        answer(
            ("Prices", ["C1", "c2", "Q1", "C9", "X1"]),
            ("“Booking”", ["C2", "C3"]),
            ("prices", ["Q2"]),
            ("Empty", ["C7"]),
            ("", ["C4"]),
        ),
        conversation_total=4,
        question_total=2,
        label_languages=EN,
    )

    assert topics is not None
    assert [
        (first_label(t), t.conversation_count, t.question_count) for t in topics
    ] == [
        ("Prices", 2, 2),
        ("Booking", 1, 0),
    ]


def test_at_most_twelve_topics_most_asked_first() -> None:
    many = [(f"Topic {number:02d}", [f"C{number}"]) for number in range(1, 16)]
    many.append(("Popular", ["C16", "C17"]))

    topics = read_grouped_topics(answer(*many), 17, 0, EN)

    assert topics is not None and len(topics) == MAX_TOPICS
    assert first_label(topics[0]) == "Popular"
    assert first_label(topics[1]) == "Topic 01"
    assert {topic.kind for topic in topics} == {TopicKind.NAMED}


def test_an_answer_without_topics_is_unreadable() -> None:
    assert read_grouped_topics("I am a test assistant.", 3, 0, EN) is None
    assert read_grouped_topics('{"groups": []}', 3, 0, EN) is None
    assert read_grouped_topics(None, 3, 0, EN) is None
    assert read_grouped_topics('{"topics": []}', 3, 0, EN) == []


def test_customer_text_is_one_short_line_without_contact_details() -> None:
    masked = mask_customer_text("Call me at +995 (555) 12-34-56\nor nino@example.com")
    long = mask_customer_text("word " * 100)

    assert masked == "Call me at [phone] or [email]"
    assert len(long) == MAX_ITEM_CHARACTERS and long.endswith("…")


def test_the_largest_languages_get_a_batch_each_the_rest_one_together() -> None:
    languages = ["ka", "ka", "ru-RU", "ru", "en", "de", "tr", "hy", None]
    messages = [
        FirstMessage(None if code is None else LanguageTag(code), f"text {number}")
        for number, code in enumerate(languages)
    ]
    question = UnansweredQuestionDocument(
        business_id=BusinessId(),
        question=UnansweredQuestionText("Parking?"),
        language=LanguageTag("ru"),
        last_seen_at=Microseconds(1),
    )

    batches = language_batches(messages, [question])

    assert [batch.language for batch in batches] == ["ka", "ru", "de", "en", None]
    assert len(batches) == MAX_TOPIC_LANGUAGES + 1
    assert batches[1].first_messages == ["text 2", "text 3"]
    assert batches[1].open_questions == ["Parking?"]
    assert batches[-1].first_messages == ["text 6", "text 7", "text 8"]
