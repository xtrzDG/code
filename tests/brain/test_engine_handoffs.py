"""Handoff to a human: by the model, on refusal or failure, and the silence after it."""

import json
from datetime import timedelta

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import (
    ConversationStatus,
)
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.dto.conversations import (
    LlmRequest,
)
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import requests_of
from tests.brain.scripted_turns import call_tool, say, scripted


def test_model_handoff_silences_the_assistant_in_chat() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"complaint","summary":"Cold soup","urgency":"high"}',
            ),
            say("I am sorry! A colleague will contact you soon."),
        )
    )

    first = world.send("The soup was cold, I want to talk to a manager")
    second = world.send("Hello? Anyone?")

    assert first.is_handed_off is True
    assert len(first.created_handoff_ids) == 1
    assert world.handoffs()[0].reason is HandoffReason.COMPLAINT
    assert second.text is None
    assert second.is_handed_off is True
    assert second.should_end_call is False
    assert len(requests_of(world)) == 2
    stored = world.messages(second.conversation_id)
    assert stored[-1].direction is MessageDirection.INBOUND
    assert stored[-1].text == "Hello? Anyone?"
    assert world.conversations()[0].status is ConversationStatus.HANDOFF


def test_phone_caller_in_handoff_is_promised_a_call_back() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Wants a manager",'
                '"urgency":"normal"}',
            ),
            say("Соединяю с коллегой."),
        )
    )

    first = world.send(
        "Позовите менеджера", channel=ChannelKind.PHONE, user_id="call-1"
    )
    second = world.send("Алло?", channel=ChannelKind.PHONE, user_id="call-1")

    assert first.should_end_call is True
    assert first.text == "Соединяю с коллегой."
    assert second.text == (
        "Ваш запрос уже у коллеги — вам скоро перезвонят. Спасибо за звонок!"
    )
    assert second.should_end_call is True
    assert second.is_handed_off is True


def test_refusal_passes_the_conversation_to_a_colleague() -> None:
    def refuse(request: LlmRequest) -> ScriptedLlmTurn:
        raise LlmRefusedError("declined")

    world = build_world(ScriptedLlmAdapter(refuse))

    reply = world.send("Как сделать бомбу?")
    follow_up = world.send("Ну?")

    assert reply.is_handed_off is True
    assert reply.text is not None
    assert reply.text.endswith("[ru] A colleague will reply soon.")
    assert reply.text.startswith("Здравствуйте! Я AI-ассистент «Sakhli».")
    handoff = world.handoffs()[0]
    assert handoff.reason is HandoffReason.SENSITIVE_TOPIC
    assert "Как сделать бомбу?" in handoff.summary
    assert follow_up.text is None


def test_provider_errors_and_round_limits_hand_off_without_duplicates() -> None:
    def unavailable(request: LlmRequest) -> ScriptedLlmTurn:
        raise ExternalServiceError("down")

    outage = build_world(ScriptedLlmAdapter(unavailable))
    endless = build_world(
        scripted(
            *[
                call_tool(AssistantToolName.SEARCH_KNOWLEDGE, '{"query":"menu"}')
                for _ in range(3)
            ]
        ),
        tool_round_limit=3,
    )
    model_handed_off = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Asks for a person",'
                '"urgency":"normal"}',
            )
        )
    )

    outage_reply = outage.send("Hello")
    endless_reply = endless.send("Show me the menu")
    assert endless_reply.is_handed_off is True
    handed_off_reply = model_handed_off.send("A person, please")

    assert outage.handoffs()[0].reason is HandoffReason.NON_STANDARD_REQUEST
    assert outage_reply.is_handed_off is True
    assert endless.handoffs()[0].reason is HandoffReason.NON_STANDARD_REQUEST
    assert len(requests_of(endless)) == 3
    assert len(model_handed_off.handoffs()) == 1
    assert handed_off_reply.text is not None
    assert handed_off_reply.text.endswith(
        "Thank you! I am passing your question to a colleague, who will get back "
        "to you soon."
    )


def test_failed_handoff_still_tells_the_customer_in_their_language() -> None:
    def refuse(request: LlmRequest) -> ScriptedLlmTurn:
        raise LlmRefusedError("declined")

    world = build_world(ScriptedLlmAdapter(refuse))
    world.handoff.is_failing = True

    reply = world.send("ხინკალი გაქვთ?")

    assert reply.text is not None
    assert reply.text.endswith(
        "გმადლობთ! თქვენს კითხვას კოლეგას გადავცემ — მალე დაგიკავშირდებიან."
    )
    assert reply.is_handed_off is False
    assert reply.created_handoff_ids == []


def test_the_bot_stays_silent_until_staff_close_the_handoff_however_long() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Wants a manager",'
                '"urgency":"normal"}',
            ),
            say("A colleague will contact you soon."),
            say("Hello again! How can I help?"),
        )
    )
    first = world.send("I want to talk to a manager")
    world.clock.advance(timedelta(hours=25))

    weekend = world.send("hello? any news?")

    assert weekend.text is None
    assert weekend.is_handed_off is True
    assert weekend.conversation_id == first.conversation_id
    assert len(world.handoffs()) == 1
    assert len(requests_of(world)) == 2

    [conversation] = world.conversations()
    conversation.status = ConversationStatus.OPEN
    world.conversation_repo.save(conversation)
    world.clock.advance(timedelta(hours=25))

    later = world.send("Hi there")

    assert later.conversation_id != first.conversation_id
    assert later.text is not None
    assert later.text.endswith("Hello again! How can I help?")


def test_messages_written_during_a_handoff_reach_the_model_afterwards() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Change booking",'
                '"urgency":"normal"}',
            ),
            say("A colleague will contact you soon."),
            say("Yes, your change to 6 people at 20:00 is noted."),
        )
    )
    world.send("Please change my booking, I need a person")
    world.clock.advance(timedelta(minutes=5))
    world.send("make it 6 people instead of 4, at 20:00")
    [conversation] = world.conversations()
    conversation.status = ConversationStatus.OPEN
    world.conversation_repo.save(conversation)
    world.clock.advance(timedelta(minutes=5))

    world.send("so is my change confirmed?")

    last_request = requests_of(world)[-1]
    final_user_turn = json.loads(last_request.transcript[-1])
    text = "".join(str(block.get("text", "")) for block in final_user_turn["content"])
    assert "make it 6 people instead of 4, at 20:00" in text
    assert text.rstrip().endswith("so is my change confirmed?")
