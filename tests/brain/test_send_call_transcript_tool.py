"""send_call_transcript: a caller asks for the call in writing (ACC-03)."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from tests.brain.brain_world import build_world
from tests.brain.scripted_turns import scripted
from tests.brain.test_voice_tool_calls import voice_call
from tests.brain.tool_runner_helpers import build_context, run_tool


def test_a_reachable_caller_is_promised_the_transcript() -> None:
    world = build_world(scripted())

    result, is_error = run_tool(
        world,
        AssistantToolName.SEND_CALL_TRANSCRIPT,
        {},
        build_context(world, channel=ChannelKind.PHONE, can_text_caller=True),
    )

    assert is_error is False
    assert result["texted_after_call"] is True
    assert "texted to them right after the call" in str(result["note"])


def test_a_caller_no_messenger_reaches_is_promised_nothing() -> None:
    world = build_world(scripted())

    result, is_error = run_tool(
        world,
        AssistantToolName.SEND_CALL_TRANSCRIPT,
        {},
        build_context(world, channel=ChannelKind.PHONE, can_text_caller=False),
    )

    assert is_error is False
    assert result["texted_after_call"] is False
    assert "do not promise one" in str(result["note"])


def test_a_voice_call_keeps_the_request_by_its_text_only() -> None:
    world = build_world(scripted())

    _, is_error = voice_call(world, AssistantToolName.SEND_CALL_TRANSCRIPT, "{}")

    assert is_error is False
    [conversation] = world.conversations()
    [message] = world.messages(conversation.id)
    assert message.author is MessageAuthor.SYSTEM
    assert str(message.text) == "Voice agent called send_call_transcript."
    assert message.tool_calls == []


def test_a_chat_is_already_in_writing() -> None:
    world = build_world(scripted())

    result, is_error = run_tool(
        world,
        AssistantToolName.SEND_CALL_TRANSCRIPT,
        {},
        build_context(world, channel=ChannelKind.WEB_CHAT),
    )

    assert is_error is True
    assert "error" in result
