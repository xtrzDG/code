"""
A caller who asks for the call in writing (send_call_transcript, ACC-03)
gets its transcript texted after the call, with any links it promised.
"""

import json

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ToolCallRecord
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.schemas.typings.channels.constrained_integers import CallOffsetSeconds
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.utilities.channels.call_transcript_message import (
    SHORTENED_MARK,
    TRANSCRIPT_MAX_CHARACTERS,
    build_call_transcript_text,
)
from app.utilities.conversations.stored_tool_calls import storable_tool_calls
from app.utilities.conversations.tool_selection import with_call_tools
from tests.channels.post_call_steps import post_call, post_call_payload
from tests.channels.test_call_links import MENU_URL, links_setup, record_send_link

TRANSCRIPT_TOOL: tuple[str, ...] = ("send_call_transcript",)


def line(
    author: MessageAuthor, text: str, offset: int = 0
) -> FinishedCallTranscriptLine:
    return FinishedCallTranscriptLine(
        author=author, text=MessageText(text), offset_seconds=CallOffsetSeconds(offset)
    )


def test_the_transcript_is_texted_when_the_caller_asked() -> None:
    setup = links_setup()

    response = post_call(setup, post_call_payload(tool_names=TRANSCRIPT_TOOL))

    assert response.status_code == 200
    [sent] = setup.testbed.telegram_transport.requests_to("/sendMessage")
    assert sent.json()["text"] == (
        "Funicular VR: თქვენი ზარის ჩანაწერი ტექსტად.\n"
        "Funicular VR: გამარჯობა! AI ასისტენტი.\n"
        "თქვენ: მაგიდა ოთხისთვის"
    )


def test_promised_links_and_the_transcript_go_in_one_message() -> None:
    setup = links_setup()
    record_send_link(setup, "menu")

    post_call(setup, post_call_payload(tool_names=("send_link", *TRANSCRIPT_TOOL)))

    [sent] = setup.testbed.telegram_transport.requests_to("/sendMessage")
    links, transcript = sent.json()["text"].split("\n\n")
    assert links.endswith(f"\n{MENU_URL}")
    assert transcript.startswith("Funicular VR: თქვენი ზარის ჩანაწერი ტექსტად.")


def test_no_transcript_is_sent_unless_the_caller_asked() -> None:
    setup = links_setup()

    post_call(setup, post_call_payload())

    assert setup.testbed.telegram_transport.requests_to("/sendMessage") == []


def test_a_call_nobody_spoke_in_sends_nothing() -> None:
    assert (
        build_call_transcript_text(
            "Header", "You", "Bar", [], is_recording_declined=False
        )
        is None
    )


def test_a_declined_recording_keeps_numbers_out_of_the_texted_transcript() -> None:
    text = build_call_transcript_text(
        "Header",
        "You",
        "Bar",
        [line(MessageAuthor.CUSTOMER, "Call me on +39 347 123 4567, a table at 20:00")],
        is_recording_declined=True,
    )

    assert text is not None
    assert "347 123 4567" not in text
    assert "a table at 20:00" in text
    assert text.splitlines()[0] == "Header"


def test_a_long_call_is_cut_at_whole_lines() -> None:
    said = "x" * 100
    lines = [line(MessageAuthor.ASSISTANT, said, index) for index in range(60)]

    text = build_call_transcript_text(
        "Header", "You", "Bar", lines, is_recording_declined=False
    )

    assert text is not None
    assert text.endswith(f"\n{SHORTENED_MARK}")
    assert len(text) <= TRANSCRIPT_MAX_CHARACTERS + 100
    assert all(row == f"Bar: {said}" for row in text.splitlines()[1:-1])


def test_system_lines_are_not_part_of_the_transcript() -> None:
    text = build_call_transcript_text(
        "Header",
        "You",
        "Bar",
        [line(MessageAuthor.SYSTEM, "Voice agent called send_link.")],
        is_recording_declined=False,
    )

    assert text is None


def test_every_call_offers_the_tool_after_its_version_tools() -> None:
    assert with_call_tools([AssistantToolName.SEND_LINK]) == [
        AssistantToolName.SEND_LINK,
        AssistantToolName.DECLINE_RECORDING,
        AssistantToolName.SEND_CALL_TRANSCRIPT,
    ]
    assert with_call_tools(
        [AssistantToolName.SEND_CALL_TRANSCRIPT, AssistantToolName.DECLINE_RECORDING]
    ) == [AssistantToolName.SEND_CALL_TRANSCRIPT, AssistantToolName.DECLINE_RECORDING]


def test_a_stored_message_never_names_the_tool_while_its_gate_is_closed() -> None:
    record = ToolCallRecord(
        tool_name=AssistantToolName.SEND_CALL_TRANSCRIPT,
        input_json=LlmToolInputJson("{}"),
        result_json=LlmToolResultJson(json.dumps({"texted_after_call": True})),
    )

    assert storable_tool_calls([record]) == []
