"""Voice utilities: call outcomes, recordings and the voice tool schemas."""

import json

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import CallOutcome, MessageAuthor
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.schemas.typings.channels.constrained_integers import CallOffsetSeconds
from app.schemas.typings.conversations.strings import (
    MessageText,
    ProviderCallId,
    RecordingStoragePath,
)
from app.utilities.channels.call_outcomes import (
    determine_call_outcome,
    render_call_transcript,
)
from app.utilities.channels.voice_recordings import (
    build_voice_platform_recording_path,
    read_voice_platform_call_id,
)
from app.utilities.channels.voice_tool_schemas import convert_tool_schema


class TestCallOutcome:
    def lines(self, *authors: MessageAuthor) -> list[FinishedCallTranscriptLine]:
        return [
            FinishedCallTranscriptLine(
                author=author,
                text=MessageText("..."),
                offset_seconds=CallOffsetSeconds(index * 5),
            )
            for index, author in enumerate(authors)
        ]

    def test_priority_of_outcomes(self) -> None:
        talk = self.lines(MessageAuthor.ASSISTANT, MessageAuthor.CUSTOMER)
        assert (
            determine_call_outcome(True, True, True, [], talk, 60)
            is CallOutcome.BOOKING
        )
        assert (
            determine_call_outcome(False, True, True, [], talk, 60) is CallOutcome.LEAD
        )
        assert (
            determine_call_outcome(False, False, True, [], talk, 60)
            is CallOutcome.HANDOFF
        )
        assert (
            determine_call_outcome(
                False, False, False, [AssistantToolName.HANDOFF_TO_HUMAN], talk, 60
            )
            is CallOutcome.HANDOFF
        )
        assert (
            determine_call_outcome(
                False,
                False,
                False,
                [AssistantToolName.RECORD_UNANSWERED_QUESTION],
                talk,
                60,
            )
            is CallOutcome.UNANSWERED_QUESTION
        )
        assert (
            determine_call_outcome(False, False, False, [], talk, 60)
            is CallOutcome.INFORMATION
        )

    def test_abandoned_calls(self) -> None:
        silent = self.lines(MessageAuthor.ASSISTANT)
        talk = self.lines(MessageAuthor.ASSISTANT, MessageAuthor.CUSTOMER)
        assert determine_call_outcome(False, False, False, [], silent, 90) is (
            CallOutcome.ABANDONED
        )
        assert determine_call_outcome(False, False, False, [], talk, 4) is (
            CallOutcome.ABANDONED
        )

    def test_transcript_rendering(self) -> None:
        assert render_call_transcript([]) is None
        rendered = render_call_transcript(
            [
                FinishedCallTranscriptLine(
                    author=MessageAuthor.ASSISTANT,
                    text=MessageText("გამარჯობა!"),
                    offset_seconds=CallOffsetSeconds(0),
                ),
                FinishedCallTranscriptLine(
                    author=MessageAuthor.CUSTOMER,
                    text=MessageText("Table for 4"),
                    offset_seconds=CallOffsetSeconds(65),
                ),
            ]
        )
        assert (
            rendered == "[00:00] assistant: გამარჯობა!\n[01:05] customer: Table for 4"
        )


class TestVoiceRecordings:
    def test_paths_round_trip(self) -> None:
        path = build_voice_platform_recording_path(ProviderCallId("conv_123"))
        assert path == "elevenlabs/conversations/conv_123"
        assert read_voice_platform_call_id(path) == "conv_123"
        for other in ("calls/2026/a.mp3", "elevenlabs/conversations/", "elevenlabs/x"):
            assert read_voice_platform_call_id(RecordingStoragePath(other)) is None


class TestVoiceToolSchemas:
    def test_json_schema_becomes_the_voice_platform_dialect(self) -> None:
        schema: dict[str, object] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "description": "Guest name"},
                "party_size": {"type": "integer", "minimum": 1},
                "starts_at": {"type": "string", "format": "date-time"},
                "notes": {"anyOf": [{"type": "null"}, {"type": "string"}]},
                "kind": {"type": "string", "enum": ["table", "room", 3]},
                "tags": {"type": "array", "items": {"type": "string"}},
                "details": {
                    "type": "object",
                    "properties": {"budget": {"type": ["string", "null"]}},
                },
            },
            "required": ["name", "party_size", "missing"],
        }
        converted = convert_tool_schema(schema, "Arguments")
        properties = converted["properties"]
        assert isinstance(properties, dict)
        assert converted["required"] == ["name", "party_size"]
        assert "additionalProperties" not in converted
        assert properties["name"] == {"type": "string", "description": "Guest name"}
        assert properties["party_size"] == {
            "type": "integer",
            "description": "party size",
        }
        assert properties["starts_at"]["description"] == "starts at (format: date-time)"
        assert properties["notes"]["type"] == "string"
        assert properties["kind"]["enum"] == ["table", "room"]
        assert properties["tags"]["items"]["type"] == "string"
        assert properties["details"]["properties"]["budget"]["type"] == "string"
        json.dumps(converted)

    def test_non_object_schemas_become_empty_objects(self) -> None:
        assert convert_tool_schema({"type": "string"}, "Arguments") == {
            "type": "object",
            "description": "Arguments",
            "properties": {},
        }
        assert convert_tool_schema({}, "Arguments")["type"] == "object"
