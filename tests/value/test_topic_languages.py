"""
Topics in the reader's language: the nightly grouping labels every topic in
each cabinet language, the catch-all is a kind (no Russian text on an
English or Georgian cabinet), and version 1 rows are upcast.
"""

import json
import re
from datetime import datetime

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.storage.topic_upgrades import upgrade_conversation_topics_from_v1
from app.schemas.constants.value import TopicKind
from app.schemas.domain.conversation_topics import (
    ConversationTopic,
    LocalizedTopicLabel,
)
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.dto.value.conversation_topics import (
    ConversationTopicsQuery,
    ConversationTopicsView,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.insights.constrained_strings import TopicLabel
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.llm_rehearsal.rehearsal_reading import read_texts
from app.utilities.llm_rehearsal.rehearsal_topics import rehearse_topics
from app.utilities.value.topic_answers import read_grouped_topics
from app.utilities.value.topic_labels import label_languages, resolve_topic_label
from tests.value.insight_bench import InsightBench
from tests.value.test_conversation_topics import busy_bench, fake_model, tick

CYRILLIC: re.Pattern[str] = re.compile(r"[Ѐ-ӿ]")


def rehearsal_model() -> ScriptedLlmAdapter:
    """The scripted provider's grouping (LLM_PROVIDER=scripted, the demo)."""

    def respond(request: LlmRequest) -> ScriptedLlmTurn:
        text: str = rehearse_topics(read_texts(str(request.transcript[-1])))
        return ScriptedLlmTurn(text=MessageText(text))

    return ScriptedLlmAdapter(respond)


def greeted_bench() -> InsightBench:
    """The busy bench and a Georgian customer who only says hello."""

    bench = busy_bench()
    hello = bench.tagged("2026-10-04T13:00:00+04:00", None, language="ka")
    bench.says(hello, "2026-10-04T13:00:00+04:00", "გამარჯობა!")
    return bench


def read(bench: InsightBench, language: str | None) -> ConversationTopicsView:
    return bench.topics().run(
        ConversationTopicsQuery(
            user_id=bench.owner.id,
            business_id=bench.business.id,
            language=None if language is None else LanguageTag(language),
        )
    )


def labels_of(view: ConversationTopicsView) -> list[tuple[str, TopicKind]]:
    return [
        (str(topic.label), topic.kind)
        for group in view.groups
        for topic in group.topics
    ]


def test_the_owner_language_comes_first_then_the_cabinet_languages() -> None:
    assert label_languages(LanguageTag("ru")) == ["ru", "en", "ka"]
    assert label_languages(LanguageTag("de-AT")) == ["de", "en", "ru", "ka"]


def test_every_cabinet_reads_the_topics_in_its_own_language() -> None:
    bench = greeted_bench()  # A Russian owner; Georgian and Russian customers.
    llm = rehearsal_model()

    assert tick(bench, llm) == 1

    assert "Label languages: ru, en, ka" in read_texts(
        str(llm.requests[0].transcript[-1])
    )
    english, georgian, russian = read(bench, "en"), read(bench, "ka"), read(bench, None)
    assert english.label_language == "en" and russian.label_language == "ru"
    assert ("Prices", TopicKind.NAMED) in labels_of(english)
    assert ("ფასები", TopicKind.NAMED) in labels_of(georgian)
    assert ("Цены", TopicKind.NAMED) in labels_of(russian)
    # The greeting fits no topic: the catch-all, named per reader.
    assert ("Other questions", TopicKind.OTHER) in labels_of(english)
    assert ("სხვა კითხვები", TopicKind.OTHER) in labels_of(georgian)
    for view in (english, georgian):
        assert not [label for label, _ in labels_of(view) if CYRILLIC.search(label)]


def test_the_catch_all_is_stored_as_a_kind_and_listed_last() -> None:
    bench = greeted_bench()
    tick(bench, rehearsal_model())

    stored = bench.topics_repo.get(bench.business.id)

    assert stored is not None and str(stored.schema_version) == "2"
    georgian = stored.groups[0].topics
    assert georgian[-1].kind is TopicKind.OTHER
    # The release before reads `label`: the catch-all's owner-language text.
    assert str(georgian[-1].label) == "Другие вопросы" and georgian[-1].labels == []
    assert {item.language for item in georgian[0].labels} == {"ru", "en", "ka"}


def test_a_missing_label_falls_back_to_english_then_the_owner_language() -> None:
    topic = ConversationTopic(
        label=TopicLabel("Парковка"),
        labels=[
            LocalizedTopicLabel(
                language=LanguageTag("ru"), label=TopicLabel("Парковка")
            ),
            LocalizedTopicLabel(
                language=LanguageTag("en"), label=TopicLabel("Parking")
            ),
        ],
        conversation_count=PeriodItemCount(2),
    )
    russian_only = ConversationTopic(
        label=TopicLabel("Доставка"), conversation_count=PeriodItemCount(1)
    )
    owner = LanguageTag("ru")

    assert resolve_topic_label(topic, LanguageTag("ka"), owner) == "Parking"
    assert resolve_topic_label(topic, LanguageTag("ru-RU"), owner) == "Парковка"
    assert resolve_topic_label(russian_only, LanguageTag("en"), owner) == "Доставка"


def test_a_model_naming_the_catch_all_still_gets_the_other_kind() -> None:
    answer = json.dumps(
        {
            "topics": [
                {
                    "labels": {"en": "Other questions", "ru": "Другие вопросы"},
                    "items": ["C1"],
                },
                {"other": True, "items": ["C2", "Q1"]},
                {"labels": {"en": "Parking", "xx": "ignored"}, "items": ["C3"]},
            ]
        }
    )

    topics = read_grouped_topics(answer, 3, 1, ["ru", "en"])

    assert topics is not None
    assert [(topic.kind, dict(topic.labels)) for topic in topics] == [
        (TopicKind.NAMED, {"en": "Parking"}),
        (TopicKind.OTHER, {}),
    ]
    assert (topics[1].conversation_count, topics[1].question_count) == (2, 1)


def test_version_1_rows_keep_their_label_and_find_their_catch_all() -> None:
    stored: dict[str, object] = {
        "label_language": "ru",
        "groups": [
            {
                "language": "ka",
                "conversation_count": 3,
                "topics": [
                    {"label": "Цены", "conversation_count": 2},
                    {"label": "Другие вопросы", "conversation_count": 1},
                ],
            }
        ],
    }

    upgraded = upgrade_conversation_topics_from_v1(stored)

    assert upgraded["groups"] == [
        {
            "language": "ka",
            "conversation_count": 3,
            "topics": [
                {
                    "label": "Цены",
                    "conversation_count": 2,
                    "labels": [{"language": "ru", "label": "Цены"}],
                    "kind": "named",
                },
                {
                    "label": "Другие вопросы",
                    "conversation_count": 1,
                    "labels": [{"language": "ru", "label": "Другие вопросы"}],
                    "kind": "other",
                },
            ],
        }
    ]
    assert upgrade_conversation_topics_from_v1({"groups": None}) == {"groups": None}


def test_the_previous_labels_offered_are_the_owner_language_ones() -> None:
    bench = greeted_bench()
    tick(bench, rehearsal_model())

    next_night = fake_model()
    bench.world.clock.move_to(datetime.fromisoformat("2026-10-06T04:00:00+04:00"))
    assert tick(bench, next_night) == 1

    offered = read_texts(str(next_night.requests[0].transcript[-1])).split("Items:")[0]
    assert "Previous labels: Бронирование; Меню и услуги" in offered
    assert "Другие вопросы" not in offered
