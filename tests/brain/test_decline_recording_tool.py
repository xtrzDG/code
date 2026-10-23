"""decline_recording: a caller says no to the recording, and the call goes on."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.conversations import MessageAuthor
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import requests_of
from tests.brain.scripted_turns import call_tool, say, scripted
from tests.brain.test_voice_tool_calls import voice_call


def test_a_caller_declines_the_recording_and_the_call_goes_on() -> None:
    world = build_world(scripted())

    result, is_error = voice_call(world, AssistantToolName.DECLINE_RECORDING, "{}")

    assert is_error is False
    assert result["recording"] == "declined"
    assert "continue helping them" in str(result["note"])
    [conversation] = world.conversations()
    [message] = world.messages(conversation.id)
    assert message.author is MessageAuthor.SYSTEM
    assert str(message.text) == "Voice agent called decline_recording."
    # Behind its closed release gate the tool call is not stored by name:
    # the voice platform's report of the call carries it.
    assert message.tool_calls == []


def test_declining_needs_no_paid_service() -> None:
    world = build_world(scripted())
    world.business.service_mode = ServiceMode.LEADS_ONLY
    world.save_business(world.business)

    result, is_error = voice_call(world, AssistantToolName.DECLINE_RECORDING, "{}")

    assert is_error is False
    assert result["recording"] == "declined"


def test_the_tool_takes_no_arguments() -> None:
    world = build_world(scripted())

    result, is_error = voice_call(
        world, AssistantToolName.DECLINE_RECORDING, '{"reason":"privacy"}'
    )

    assert is_error is True
    assert "error" in result


def test_a_chat_is_not_offered_the_tool_and_cannot_call_it() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.DECLINE_RECORDING, "{}"),
            say("This chat is not recorded."),
        )
    )

    world.send("Please do not record me")

    offered = [tool.name for tool in requests_of(world)[0].tools]
    assert AssistantToolName.DECLINE_RECORDING not in offered
    reply = world.messages(world.conversations()[0].id)[-1]
    assert reply.tool_calls == []
