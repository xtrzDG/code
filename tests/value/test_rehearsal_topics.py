"""
The rehearsal's grouping of first messages (LLM_PROVIDER=scripted and the
demo): each message under the topic its words name, labels in the
requested language, read back as the real model's answer is.
"""

import json

from app.schemas.constants.value import TopicKind
from app.utilities.llm_rehearsal.rehearsal_topics import (
    RehearsalTopic,
    classify_topic,
    rehearse_topics,
)
from app.utilities.value.topic_answers import read_grouped_topics
from app.utilities.value.topic_grouping import build_topic_request_text


def test_messages_go_to_the_topic_their_words_name() -> None:
    assert classify_topic("Забронируйте стол на завтра") is RehearsalTopic.BOOKING
    assert classify_topic("Отмените, пожалуйста, бронь") is RehearsalTopic.BOOKING
    # "How many" asks about the time here, not the price.
    assert classify_topic("Во сколько вы открываетесь?") is RehearsalTopic.HOURS
    assert classify_topic("Сколько стоит хачапури?") is RehearsalTopic.PRICES
    assert classify_topic("Дайте скидку 10 %") is RehearsalTopic.PRICES
    assert classify_topic("რომელ საათზე იხსნებით?") is RehearsalTopic.HOURS
    assert classify_topic("Is there parking nearby?") is RehearsalTopic.PLACE
    assert classify_topic("Do you have vegan dishes?") is RehearsalTopic.OFFER
    assert classify_topic("В четверг день рождения, нас 8") is RehearsalTopic.EVENTS
    assert classify_topic("Хинкали ждали 40 минут") is RehearsalTopic.COMPLAINT
    assert classify_topic("Соедините с живым человеком") is RehearsalTopic.OTHER


def test_the_answer_reads_back_in_the_requested_language() -> None:
    request = build_topic_request_text(
        ["ru", "en", "ka"],
        "Mtsvane Ezo",
        [],
        ["Забронируйте стол на двоих", "Во сколько вы открываетесь?"],
        ["Есть рядом зарядка для электромобиля?"],
    )

    answer = rehearse_topics(request)
    topics = read_grouped_topics(
        answer,
        conversation_total=2,
        question_total=1,
        label_languages=["ru", "en", "ka"],
    )

    assert json.loads(answer)["topics"][0]["items"] == ["C1"]
    assert json.loads(answer)["topics"][2] == {"other": True, "items": ["Q1"]}
    assert topics is not None
    counts = [
        (topic.kind, dict(topic.labels), topic.conversation_count, topic.question_count)
        for topic in topics
    ]
    assert counts == [
        (
            TopicKind.NAMED,
            {"ru": "Бронирование", "en": "Booking", "ka": "ჯავშანი"},
            1,
            0,
        ),
        (
            TopicKind.NAMED,
            {"ru": "Часы работы", "en": "Opening hours", "ka": "სამუშაო საათები"},
            1,
            0,
        ),
        (TopicKind.OTHER, {}, 0, 1),
    ]


def test_a_language_without_labels_gets_english_ones() -> None:
    request = build_topic_request_text(["fr"], "Café", [], ["Can I book a table?"], [])

    topics = read_grouped_topics(rehearse_topics(request), 1, 0, ["fr"])

    assert topics is not None
    assert [dict(topic.labels) for topic in topics] == [{"fr": "Booking"}]
