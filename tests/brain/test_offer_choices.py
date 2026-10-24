"""
The offer_choices tool in the engine: where it is offered, what it refuses,
how the options travel with the reply and how the guard reads them; and
the story context of an Instagram message.
"""

import json

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, InboundContextNote
from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.conversations.tool_selection import select_available_tools
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.scripted_turns import call_tool, say, scripted


def offer(options: list[str], prompt: str = "Which time suits you?") -> str:
    return json.dumps({"prompt_text": prompt, "options": options}, ensure_ascii=False)


@pytest.mark.parametrize(
    ("channel", "is_offered"),
    [
        (ChannelKind.PHONE, False),
        (ChannelKind.TELEGRAM, True),
        (ChannelKind.WHATSAPP, True),
        (ChannelKind.INSTAGRAM, True),
        (ChannelKind.WEB_CHAT, True),
    ],
)
def test_offered_in_every_chat_channel_but_not_on_the_phone(
    channel: ChannelKind, is_offered: bool
) -> None:
    world = build_world(scripted(say("…")))

    tools = select_available_tools(world.version, world.business, channel)

    assert (AssistantToolName.OFFER_CHOICES in tools) is is_offered
    # The version itself does not list it (its release gate is closed).
    assert AssistantToolName.OFFER_CHOICES not in world.version.tools


def test_the_reply_ends_with_the_question_and_carries_the_options() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.OFFER_CHOICES, offer(["Yes", "No"], "Shall I?")
            ),
            say("A table for 2 tomorrow at 19:30."),
        )
    )

    reply = world.send("A table for 2 tomorrow at 19:30?", channel=ChannelKind.WEB_CHAT)

    assert reply.text is not None
    assert str(reply.text).endswith("A table for 2 tomorrow at 19:30.\n\nShall I?")
    assert reply.choices is not None
    assert [str(option) for option in reply.choices.options] == ["Yes", "No"]
    assert str(reply.choices.language) == "en"
    stored = world.messages(reply.conversation_id)[-1]
    assert stored.choices == reply.choices
    assert stored.text == reply.text


@pytest.mark.parametrize(
    "options",
    [
        ["Only one"],
        [f"Option {number}" for number in range(11)],
        ["A label longer than twenty", "No"],
        ["Yes", "YES"],
        ["Yes", " "],
    ],
)
def test_options_that_cannot_be_tapped_are_refused(options: list[str]) -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.OFFER_CHOICES, offer(options)),
            say("We have tables tonight."),
        )
    )

    reply = world.send("A table tonight?", channel=ChannelKind.TELEGRAM)

    assert reply.choices is None
    assert reply.is_handed_off is False
    tool_results = user_turn_text(requests_of(world)[1].transcript[-1])
    assert "shown" not in tool_results


def test_the_last_call_of_a_turn_wins() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.OFFER_CHOICES, offer(["18:00", "19:30"])),
            call_tool(AssistantToolName.OFFER_CHOICES, offer(["19:30", "20:00"])),
            say("We have a table."),
        )
    )

    reply = world.send(
        "A table tonight at 18:00, 19:30 or 20:00?", channel=ChannelKind.TELEGRAM
    )

    assert reply.choices is not None
    assert [str(option) for option in reply.choices.options] == ["19:30", "20:00"]


def test_the_guard_reads_the_options_with_the_reply() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.OFFER_CHOICES,
                offer(["Menu for 90 ₾", "No"], "Shall I add it?"),
            ),
            say("We have a set menu."),
            call_tool(
                AssistantToolName.OFFER_CHOICES, offer(["Yes", "No"], "Shall I?")
            ),
            say("We have a set menu."),
        )
    )

    reply = world.send("Do you have a set menu?", channel=ChannelKind.TELEGRAM)

    # An invented price in an option is caught like one in the text.
    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert reply.choices is not None
    assert [str(option) for option in reply.choices.options] == ["Yes", "No"]


def test_a_handed_off_reply_offers_nothing() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.OFFER_CHOICES, offer(["Yes", "No"])),
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Wants a manager",'
                '"urgency":"normal"}',
            ),
            say("A colleague will reply soon."),
        )
    )

    reply = world.send("Call me a manager", channel=ChannelKind.TELEGRAM)

    assert reply.is_handed_off is True
    assert reply.choices is None
    assert world.messages(reply.conversation_id)[-1].choices is None


@pytest.mark.parametrize(
    ("note", "expected"),
    [
        (InboundContextNote.STORY_REPLY, "a reply to the business's Instagram story"),
        (
            InboundContextNote.STORY_MENTION,
            "a mention of the business in the customer's own Instagram story",
        ),
    ],
)
def test_a_story_reply_or_mention_is_an_untrusted_context_line(
    note: InboundContextNote, expected: str
) -> None:
    world = build_world(scripted(say("Thank you!")))

    reply = world.pipeline.start(
        InboundMessage(
            business_id=world.business.id,
            channel=ChannelKind.INSTAGRAM,
            channel_user_id=ChannelUserId("igsid-1"),
            text=MessageText("Is this still available?"),
            context_note=note,
        )
    )

    turn = user_turn_text(requests_of(world)[0].transcript[0])
    assert "Message context: <untrusted" in turn
    assert expected in turn
    customer_message = world.messages(reply.conversation_id)[0]
    assert customer_message.context_note is note
