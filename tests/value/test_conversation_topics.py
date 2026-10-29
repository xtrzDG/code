"""What customers ask about: the nightly grouping and the Overview card's read."""

import json
from datetime import datetime

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.dto.value.conversation_topics import ConversationTopicsQuery
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.value.topic_grouping import TOPIC_SYSTEM_PROMPT
from tests.value.insight_bench import InsightBench
from tests.value.value_scene import at

GROUPED = {
    "topics": [
        {"label": "Бронирование", "items": ["C2"]},
        {"label": "Цены", "items": ["C1", "Q1", "C1"]},
    ]
}


def fake_model(answer: object = GROUPED) -> ScriptedLlmAdapter:
    """The same grouping for every language (a deterministic cheap model)."""

    def respond(request: LlmRequest) -> ScriptedLlmTurn:
        del request
        return ScriptedLlmTurn(text=MessageText(json.dumps(answer)))

    return ScriptedLlmAdapter(respond)


def tick(bench: InsightBench, llm: ScriptedLlmAdapter) -> int:
    report = bench.topics_job(llm).run(
        JobTick(
            job_name=JobName("group_conversation_topics"),
            scheduled_at=bench.world.clock.now_microseconds(),
        )
    )
    return int(report.processed_count)


def request_text(request: LlmRequest) -> str:
    return json.dumps(json.loads(str(request.transcript[0])), ensure_ascii=False)


def busy_bench() -> InsightBench:
    bench = InsightBench()
    first = bench.tagged("2026-10-01T13:00:00+04:00", "qr", language="ka")
    second = bench.tagged("2026-10-02T13:00:00+04:00", None, language="ka")
    russian = bench.tagged(
        "2026-10-03T13:00:00+04:00", None, ChannelKind.TELEGRAM, language="ru"
    )
    bench.says(first, "2026-10-01T13:00:00+04:00", "რა ღირს მაგიდა? +995 555 12 34 56")
    bench.says(first, "2026-10-01T13:05:00+04:00", "And for ten people?")
    bench.says(second, "2026-10-02T13:00:00+04:00", "Can I book for Friday?")
    bench.says(russian, "2026-10-03T13:00:00+04:00", "Сколько стоит ужин?")
    old = bench.tagged("2026-08-01T13:00:00+04:00", None, language="ka")
    bench.says(old, "2026-08-01T13:00:00+04:00", "Too old to count")
    sandbox = bench.tagged("2026-10-03T14:00:00+04:00", None, is_sandbox=True)
    bench.says(sandbox, "2026-10-03T14:00:00+04:00", "Owner testing")
    bench.world.question_repo.save(
        UnansweredQuestionDocument(
            business_id=bench.business.id,
            question=UnansweredQuestionText("Do you have a kids menu?"),
            language=LanguageTag("ka"),
            last_seen_at=at("2026-10-02T13:00:00+04:00"),
        )
    )
    return bench


def test_a_business_never_grouped_is_grouped_at_once() -> None:
    bench = busy_bench()
    llm = fake_model()

    assert tick(bench, llm) == 1

    stored = bench.topics_repo.get(bench.business.id)
    assert stored is not None
    georgian, russian = stored.groups
    assert (georgian.language, georgian.conversation_count) == ("ka", 2)
    assert [
        (t.label, t.conversation_count, t.unanswered_count) for t in georgian.topics
    ] == [
        ("Цены", 1, 1),
        ("Бронирование", 1, 0),
    ]
    # The Russian batch has one item: C2 and Q1 are unknown there.
    assert [(t.label, t.conversation_count) for t in russian.topics] == [("Цены", 1)]
    [ka_request, ru_request] = llm.requests
    assert str(ka_request.system_prompt) == TOPIC_SYSTEM_PROMPT
    text = request_text(ka_request)
    assert "Previous labels: none" in text
    assert "[phone]" in text and "555 12 34" not in text
    assert "And for ten people" not in text  # only the first message
    assert "Too old" not in text and "Owner testing" not in text
    assert "Q1: Do you have a kids menu?" in text
    assert "Сколько стоит ужин?" in request_text(ru_request)


def test_the_topics_stay_stable_night_after_night() -> None:
    bench = busy_bench()
    tick(bench, fake_model())
    first = bench.topics_repo.get(bench.business.id)

    later_today = fake_model()
    bench.world.clock.move_to(datetime.fromisoformat("2026-10-05T23:00:00+04:00"))
    assert tick(bench, later_today) == 0
    assert later_today.requests == []

    next_night = fake_model()
    bench.world.clock.move_to(datetime.fromisoformat("2026-10-06T04:00:00+04:00"))
    assert tick(bench, next_night) == 1

    second = bench.topics_repo.get(bench.business.id)
    assert first is not None and second is not None
    assert second.groups == first.groups
    assert second.window_to > first.window_to
    assert "Previous labels: Цены; Бронирование" in request_text(next_night.requests[0])


def test_an_unreadable_answer_keeps_the_stored_topics() -> None:
    bench = busy_bench()
    tick(bench, fake_model())
    stored = bench.topics_repo.get(bench.business.id)
    bench.world.clock.move_to(datetime.fromisoformat("2026-10-06T04:00:00+04:00"))

    assert tick(bench, fake_model("I am a test assistant")) == 0

    assert bench.topics_repo.get(bench.business.id) == stored


def test_nothing_to_group_costs_no_model_call() -> None:
    bench = InsightBench()
    llm = fake_model()

    assert tick(bench, llm) == 1

    stored = bench.topics_repo.get(bench.business.id)
    assert stored is not None and stored.groups == []
    assert llm.requests == []


def test_owners_and_staff_read_the_topics_largest_language_first() -> None:
    bench = busy_bench()
    query = ConversationTopicsQuery(
        user_id=bench.staff_id, business_id=bench.business.id
    )

    empty = bench.topics().run(query)
    tick(bench, fake_model())
    view = bench.topics().run(query)

    assert (empty.groups, empty.window_to) == ([], None)
    assert empty.label_language == bench.business.owner_language
    assert [group.language for group in view.groups] == ["ka", "ru"]
    assert view.groups[0].topics[0].unanswered_count == 1
