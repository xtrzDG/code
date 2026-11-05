"""Business rules around a turn: leads-only mode, contact limits, versions, hours."""

from datetime import timedelta

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import ServiceMode
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.scripted_turns import call_tool, say, scripted


def test_leads_only_mode_offers_only_requests_and_handoff() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.CREATE_BOOKING,
                '{"name":"Ann","phone":null,"resource_type":null,"date":"2026-10-02",'
                '"time":"19:00","party_size":2,"duration_minutes":null,'
                '"nights":null,"notes":null}',
            ),
            call_tool(
                AssistantToolName.CREATE_LEAD,
                '{"lead_type":"other","details":"Table for 2 tomorrow at 19:00",'
                '"name":"Ann","phone":null,"requested_date":"2026-10-02",'
                '"party_size":2,"budget":null}',
            ),
            say("I passed your request for tomorrow at 19:00 to the manager."),
        )
    )
    world.business.service_mode = ServiceMode.LEADS_ONLY
    world.save_business(world.business)

    reply = world.send("Table for 2 tomorrow at 19:00 please")

    request = requests_of(world)[0]
    # A customer may still ask about the bookings they already have.
    assert {tool.name for tool in request.tools} == {
        AssistantToolName.CREATE_LEAD,
        AssistantToolName.HANDOFF_TO_HUMAN,
        AssistantToolName.SEARCH_KNOWLEDGE,
        AssistantToolName.LIST_MY_BOOKINGS,
        AssistantToolName.OFFER_CHOICES,
    }
    assert "Bookings are paused" in user_turn_text(request.transcript[0])
    assert world.bookings.commands == []
    assert len(reply.created_lead_ids) == 1
    outbound = world.messages(reply.conversation_id)[-1]
    assert outbound.tool_calls[0].is_error is True
    assert "not available" in outbound.tool_calls[0].result_json


def test_contact_limit_answers_once_then_stays_silent_for_the_hour() -> None:
    world = build_world(
        scripted(say("Привет!"), say("Да."), say("Снова здравствуйте!")),
        contact_message_limit=2,
    )

    answers = [world.send(text).text for text in ("Привет", "Есть меню?")]
    notice = world.send("А?")
    silence = world.send("Ау!")
    world.clock.advance(timedelta(hours=1, minutes=1))
    after_an_hour = world.send("Здравствуйте")

    assert answers[1] == "Да."
    assert notice.text == (
        "Вы отправили много сообщений за короткое время. Пожалуйста, напишите "
        "чуть позже — мы с радостью продолжим."
    )
    assert silence.text is None
    assert after_an_hour.text == "Снова здравствуйте!"
    assert len(requests_of(world)) == 3


def test_conversations_stay_pinned_to_their_version() -> None:
    world = build_world(scripted(say("v1 answer"), say("still v1"), say("v2 answer")))
    first = world.send("Hi")
    newer: AssistantVersionDocument = world.version.model_copy(
        update={
            "id": AssistantVersionId(),
            "version_number": AssistantVersionNumber(2),
            "prompt_text": SystemPromptText("You are version two."),
        }
    )
    world.version_repo.save(newer)
    world.business.published_assistant_version_id = newer.id
    world.save_business(world.business)

    world.clock.advance(timedelta(hours=23))
    same = world.send("Still there?")
    world.clock.advance(timedelta(hours=25))
    new = world.send("Hello again")

    prompts = [str(request.system_prompt) for request in requests_of(world)]
    assert prompts == [
        "You are the AI assistant of Sakhli.",
        "You are the AI assistant of Sakhli.",
        "You are version two.",
    ]
    assert same.conversation_id == first.conversation_id
    assert new.conversation_id != first.conversation_id
    assert new.text is not None
    assert new.text.startswith("Hello! I am the AI assistant of Sakhli.")


def test_requested_versions_must_exist_and_a_business_needs_a_published_one() -> None:
    unpublished = build_world(scripted(say("x")), is_published=False)
    world = build_world(scripted(say("x")))

    with pytest.raises(ConflictError, match="no published assistant"):
        unpublished.send("Hi")

    with pytest.raises(NotFoundError):
        world.send("Hi", version_id=world.version.id.__class__(), is_sandbox=True)


def test_after_hours_flag_follows_the_business_time_zone_and_holidays() -> None:
    world = build_world(scripted(say("Ночью мы закрыты."), say("Сегодня праздник.")))
    world.clock.advance(timedelta(hours=12))

    night = world.send("Вы открыты?")
    world.clock.advance(timedelta(hours=12))
    world.exception_repo.save(
        ScheduleExceptionDocument(
            business_id=world.business.id,
            date=LocalDate("2026-10-02"),
        )
    )
    holiday = world.send("А сейчас?", user_id="another", phone=None)

    conversations = {
        conversation.id: conversation for conversation in world.conversations()
    }
    assert conversations[night.conversation_id].is_after_hours is True
    assert conversations[holiday.conversation_id].is_after_hours is True
    night_turn = user_turn_text(requests_of(world)[0].transcript[0])
    assert "Thursday 2026-10-01 02:00" not in night_turn
    assert "Friday 2026-10-02 02:00 (Asia/Tbilisi)" in night_turn
    assert "The business is closed right now" in night_turn


def test_open_hours_are_not_flagged() -> None:
    world = build_world(scripted(say("Да, открыты.")))

    reply = world.send("Вы открыты?")

    assert world.conversations()[0].is_after_hours is False
    assert reply.language == LanguageTag("ru")
