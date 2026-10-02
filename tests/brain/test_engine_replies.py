"""The engine's replies: disclosure, language, tool rounds, usage and transcript."""

import json
from typing import Any

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import (
    LlmTurnRole,
    MessageAuthor,
    ReplyGuardVerdict,
)
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.bookings.constrained_strings import LocalDate
from tests.brain.brain_world import build_world
from tests.brain.business_setups import ARMENIA, BRAZIL, ISRAEL
from tests.brain.engine_helpers import CountingLlmAdapter, requests_of, user_turn_text
from tests.brain.scripted_turns import call_tool, say, scripted


def test_first_reply_starts_with_the_localized_disclosure_only_once() -> None:
    world = build_world(
        scripted(say("რით შემიძლია დაგეხმაროთ?"), say("ხვალ 12:00-დან ვართ ღია."))
    )

    first = world.send("გამარჯობა!")
    second = world.send("ხვალ რომელ საათზე იხსნებით?")

    assert first.text == (
        "გამარჯობა! მე ვარ Sakhli-ის AI-ასისტენტი.\nრით შემიძლია დაგეხმაროთ?"
    )
    assert first.language == "ka"
    assert second.text == "ხვალ 12:00-დან ვართ ღია."
    assert first.conversation_id == second.conversation_id
    first_turn_text = user_turn_text(requests_of(world)[0].transcript[0])
    second_turn_text = user_turn_text(requests_of(world)[1].transcript[-1])
    assert "Local time at the business: Thursday 2026-10-01 14:00 (Asia/Tbilisi)." in (
        first_turn_text
    )
    assert "Next days: Fri 2026-10-02, Sat 2026-10-03" in first_turn_text
    assert "Channel: whatsapp." in first_turn_text
    assert "Customer: phone +995555123456." in first_turn_text
    assert "first reply in this conversation" in first_turn_text
    assert first_turn_text.endswith("[Customer message]\nგამარჯობა!")
    assert "first reply" not in second_turn_text


@pytest.mark.parametrize(
    ("setup", "text", "language", "disclosure"),
    [
        (ISRAEL, "שלום, יש לכם שולחן פנוי?", "he", "שלום! אני עוזר ה-AI של Beit Kafe."),
        (
            ISRAEL,
            "مرحبا، هل لديكم طاولة؟",
            "ar",
            "مرحبًا! أنا مساعد الذكاء الاصطناعي لدى Beit Kafe.",
        ),
        (
            ISRAEL,
            "Привет, есть столик?",
            "ru",
            "Здравствуйте! Я AI-ассистент «Beit Kafe».",
        ),
        (
            ARMENIA,
            "Բարև, սեղան ունե՞ք",
            "hy",
            "Բարև Ձեզ։ Ես Ararat Grill-ի AI օգնականն եմ։",
        ),
        (
            BRAZIL,
            "Olá, vocês têm mesa?",
            "pt-BR",
            "Olá! Sou o assistente de IA de Cantina Sol.",
        ),
        (
            BRAZIL,
            "Hola, ¿tienen mesa?",
            "es",
            "¡Hola! Soy el asistente de IA de Cantina Sol.",
        ),
    ],
)
def test_language_is_detected_among_the_version_languages(
    setup: Any,
    text: str,
    language: str,
    disclosure: str,
) -> None:
    world = build_world(scripted(say("…")), setup)

    reply = world.send(text, phone=None)

    assert reply.language == language
    assert reply.text is not None
    assert reply.text.startswith(disclosure)
    stored = world.messages(reply.conversation_id)
    assert [message.language for message in stored] == [language, language]
    assert world.contacts()[0].language == language


def test_booking_flow_runs_tool_rounds_and_stores_everything() -> None:
    llm = CountingLlmAdapter(
        scripted(
            call_tool(
                AssistantToolName.CHECK_AVAILABILITY,
                '{"resource_type":"table","date":"2026-10-02","time":"19:30",'
                '"party_size":4,"duration_minutes":null,"nights":null}',
            ),
            call_tool(
                AssistantToolName.CREATE_BOOKING,
                '{"name":"Нино","phone":null,"resource_type":"table",'
                '"date":"2026-10-02","time":"19:30","party_size":4,'
                '"duration_minutes":null,"nights":null,"notes":null}',
            ),
            say("Готово! Столик на 4 человек 2 октября в 19:30 на имя Нино."),
        ),
        input_tokens=10_000,
        output_tokens=1_000,
    )
    world = build_world(llm)
    world.version.model_id = LlmModelId("gpt-5-mini")
    world.version_repo.save(world.version)

    reply = world.send("Хочу столик завтра на 4 человек в 19:30", name="Нино")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert len(reply.created_booking_ids) == 1
    assert reply.is_handed_off is False
    assert reply.text is not None
    assert reply.text.endswith("на имя Нино.")
    contact = world.contacts()[0]
    command = world.bookings.commands[0]
    assert isinstance(command, CreateBookingCommand)
    assert command.business_id == world.business.id
    assert command.contact_id == contact.id
    assert command.conversation_id == reply.conversation_id
    assert command.contact_phone_number == "+995555123456"
    assert command.source_channel is ChannelKind.WHATSAPP
    assert command.language == "ru"
    assert command.date == LocalDate("2026-10-02")
    assert world.availability.queries[0].business_id == world.business.id

    turns = world.turns(reply.conversation_id)
    assert [int(turn.sequence_number) for turn in turns] == [0, 1, 2, 3, 4, 5]
    assert [turn.role for turn in turns] == [
        LlmTurnRole.USER,
        LlmTurnRole.ASSISTANT,
        LlmTurnRole.USER,
        LlmTurnRole.ASSISTANT,
        LlmTurnRole.USER,
        LlmTurnRole.ASSISTANT,
    ]
    tool_results_turn = json.loads(turns[2].payload)
    assert tool_results_turn["content"][0]["type"] == "tool_result"
    assert len(llm.inner.requests) == 3
    assert len(llm.inner.requests[2].transcript) == 5
    assert [tool.name for tool in llm.inner.requests[0].tools] == list(
        AssistantToolName
    )

    outbound = world.messages(reply.conversation_id)[-1]
    assert outbound.direction is MessageDirection.OUTBOUND
    assert outbound.author is MessageAuthor.ASSISTANT
    assert [record.tool_name for record in outbound.tool_calls] == [
        AssistantToolName.CHECK_AVAILABILITY,
        AssistantToolName.CREATE_BOOKING,
    ]
    assert outbound.model_id == "gpt-5-mini"
    assert (int(outbound.input_tokens), int(outbound.output_tokens)) == (30_000, 3_000)
    assert int(outbound.cost_micro_usd) == 30_000 * 0.25 + 3_000 * 2
    usage = {event.kind: event for event in world.usage_events()}
    assert int(usage[UsageKind.LLM_INPUT_TOKENS].quantity) == 30_000
    assert int(usage[UsageKind.LLM_INPUT_TOKENS].cost_micro_usd) == 7_500
    assert int(usage[UsageKind.LLM_OUTPUT_TOKENS].cost_micro_usd) == 6_000
    assert int(usage[UsageKind.DIALOG].quantity) == 1


def test_dialog_usage_is_counted_once_per_conversation() -> None:
    world = build_world(scripted(say("Да."), say("Конечно.")))

    world.send("Здравствуйте")
    world.send("Есть веранда?")

    assert [event.kind for event in world.usage_events()] == [UsageKind.DIALOG]


def test_transcript_is_append_only_across_messages() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.GET_PRICE, '{"item_name":"khachapuri"}'),
            say("Adjarian khachapuri costs 18 GEL."),
            say("You are welcome!"),
        )
    )

    first = world.send("How much is khachapuri?")
    first_turns = [
        (turn.id, turn.payload) for turn in world.turns(first.conversation_id)
    ]
    second = world.send("Thanks!")
    all_turns = world.turns(second.conversation_id)

    assert first.conversation_id == second.conversation_id
    assert [(turn.id, turn.payload) for turn in all_turns[:4]] == first_turns
    assert [int(turn.sequence_number) for turn in all_turns] == list(range(6))
    assert requests_of(world)[2].transcript[:4] == [
        payload for _, payload in first_turns
    ]


def test_phone_goodbye_ends_the_call_and_phone_replies_skip_the_disclosure() -> None:
    world = build_world(scripted(say("Будем рады вас видеть!"), say("Всего доброго!")))

    first = world.send(
        "Вы работаете завтра?", channel=ChannelKind.PHONE, user_id="call-7"
    )
    second = world.send(
        "Спасибо, до свидания!", channel=ChannelKind.PHONE, user_id="call-7"
    )

    assert first.text == "Будем рады вас видеть!"
    assert first.should_end_call is False
    assert second.should_end_call is True
