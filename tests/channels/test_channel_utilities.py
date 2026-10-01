import json

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import CallOutcome, MessageAuthor
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.schemas.typings.channels.constrained_integers import CallOffsetSeconds
from app.schemas.typings.channels.constrained_strings import ManagerLinkCode
from app.schemas.typings.conversations.strings import (
    MessageText,
    ProviderCallId,
    RecordingStoragePath,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
    TimezoneName,
)
from app.utilities.channels.call_outcomes import (
    determine_call_outcome,
    render_call_transcript,
)
from app.utilities.channels.channel_phone_numbers import (
    parse_messaging_phone_number,
)
from app.utilities.channels.json_values import (
    parse_json_object,
    read_identifier,
    read_integer,
    read_number,
    read_objects,
    read_text,
)
from app.utilities.channels.language_codes import (
    from_voice_platform_language,
    to_voice_platform_language,
    to_whatsapp_template_language,
)
from app.utilities.channels.local_moments import format_local_moment
from app.utilities.channels.manager_link_codes import (
    generate_link_code,
    hash_link_code,
    read_link_code,
)
from app.utilities.channels.message_chunks import split_message_text, utf16_length
from app.utilities.channels.voice_recordings import (
    build_voice_platform_recording_path,
    read_voice_platform_call_id,
)
from app.utilities.channels.voice_tool_schemas import convert_tool_schema
from app.utilities.localization.phone_number_parser import PhoneNumberParser

# 2026-10-03 15:30 UTC.
MOMENT: int = 1_791_041_400


class TestMessageChunks:
    def test_short_text_is_one_part(self) -> None:
        assert split_message_text("  Hello!  ", 4096) == ["Hello!"]
        assert split_message_text("   ", 10) == []

    def test_breaks_at_paragraphs_then_sentences_then_words(self) -> None:
        text: str = "First paragraph here.\n\nSecond one is longer. It has two."
        assert split_message_text(text, 30) == [
            "First paragraph here.",
            "Second one is longer.",
            "It has two.",
        ]

    def test_hard_cut_without_spaces(self) -> None:
        assert split_message_text("a" * 25, 10) == ["a" * 10, "a" * 10, "a" * 5]

    def test_emoji_count_as_two_units(self) -> None:
        parts: list[str] = split_message_text("😀" * 5, 4)
        assert parts == ["😀😀", "😀😀", "😀"]
        assert all(utf16_length(part) <= 4 for part in parts)

    def test_right_to_left_and_georgian_text(self) -> None:
        hebrew: str = "שלום לכולם. " * 30
        georgian: str = "გამარჯობა მეგობრებო. " * 30
        for text in (hebrew, georgian):
            parts: list[str] = split_message_text(text, 100)
            assert all(utf16_length(part) <= 100 for part in parts)
            assert " ".join(parts).split() == text.split()

    def test_limit_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            split_message_text("text", 0)


class TestMessagingPhoneNumbers:
    parser = PhoneNumberParser()

    @pytest.mark.parametrize(
        ("raw_number", "expected"),
        [
            ("995599123456", "+995599123456"),  # Georgia (WhatsApp id)
            ("37477123456", "+37477123456"),  # Armenia
            ("972502345678", "+972502345678"),  # Israel
            ("77710009998", "+77710009998"),  # Kazakhstan
            ("48512345678", "+48512345678"),  # Poland
            ("12025550123", "+12025550123"),  # United States
            ("5511961234567", "+5511961234567"),  # Brazil
            ("551187654321", "+5511987654321"),  # Brazil without the 9th digit
            ("+995 599 12 34 56", "+995599123456"),  # Telegram contact format
        ],
    )
    def test_numbers_of_many_countries(self, raw_number: str, expected: str) -> None:
        assert parse_messaging_phone_number(self.parser, raw_number) == expected

    def test_invalid_numbers_read_as_unknown(self) -> None:
        for raw_number in ("123", "", "not a number", "9" * 40, "+800 1234 5678"):
            assert parse_messaging_phone_number(self.parser, raw_number) is None

    def test_national_format_uses_the_country_hint(self) -> None:
        assert (
            parse_messaging_phone_number(
                self.parser, "0599 12 34 56", CountryCode("GE")
            )
            == "+995599123456"
        )


class TestLanguageCodes:
    @pytest.mark.parametrize(
        ("tag", "voice_code", "template_code"),
        [
            ("en", "en", "en"),
            ("ka", "ka", "ka"),
            ("pt-BR", "pt-br", "pt_BR"),
            ("pt-PT", "pt", "pt_PT"),
            ("zh-Hant-TW", "zh", "zh_TW"),
            ("he", "he", "he"),
            ("es-419", "es", "es"),
        ],
    )
    def test_codes(self, tag: str, voice_code: str, template_code: str) -> None:
        assert to_voice_platform_language(LanguageTag(tag)) == voice_code
        assert to_whatsapp_template_language(LanguageTag(tag)) == template_code

    def test_voice_codes_back_to_tags(self) -> None:
        assert from_voice_platform_language("pt-br") == "pt-BR"
        assert from_voice_platform_language("KA") == "ka"
        assert from_voice_platform_language("not a language") is None


class TestLocalMoments:
    def test_moment_in_business_time_zone_and_language(self) -> None:
        tbilisi = TimezoneName("Asia/Tbilisi")
        assert format_local_moment(MOMENT, tbilisi, LanguageTag("ru")).endswith("19:30")
        assert "7:30" in format_local_moment(MOMENT, tbilisi, LanguageTag("en"))
        assert "2026" in format_local_moment(MOMENT, tbilisi, LanguageTag("ka"))
        # Israel is on summer time (UTC+3) until the end of October.
        assert "18:30" in format_local_moment(
            MOMENT, TimezoneName("Asia/Jerusalem"), LanguageTag("he")
        )
        new_york = format_local_moment(
            MOMENT, TimezoneName("America/New_York"), LanguageTag("en")
        )
        assert "11:30" in new_york

    def test_unknown_zone_and_language_fall_back(self) -> None:
        text: str = format_local_moment(
            MOMENT, TimezoneName("Mars/Olympus"), LanguageTag("zz")
        )
        assert "3:30" in text and "2026" in text


class TestLinkCodes:
    def test_generated_codes_are_valid_and_hashed(self) -> None:
        codes: set[str] = {str(generate_link_code()) for _ in range(50)}
        assert len(codes) == 50
        code: ManagerLinkCode = generate_link_code()
        assert hash_link_code(code) == hash_link_code(ManagerLinkCode(str(code)))
        assert str(code) not in hash_link_code(code)

    def test_typed_codes_are_normalized(self) -> None:
        assert read_link_code(" 7kq2 m9xh4d ") == "7KQ2M9XH4D"
        for broken in ("", "SHORT", "ILLEGAL0OU", "7KQ2M9XH4D9"):
            assert read_link_code(broken) is None


class TestJsonValues:
    def test_defensive_reading(self) -> None:
        source = parse_json_object(
            b'{"a": 1, "b": true, "c": "  ", "d": [1, {"x": 2}], "e": 1.5,'
            b' "f": "7", "g": NaN}'
        )
        assert source is not None
        assert read_integer(source, "a") == 1
        assert read_integer(source, "b") is None
        assert read_text(source, "c") is None
        assert read_objects(source, "d") == [{"x": 2}]
        assert read_number(source, "e") == 1.5
        assert read_number(source, "g") is None
        assert read_identifier(source, "a") == "1"
        assert read_identifier(source, "f") == "7"
        assert read_identifier(source, "b") is None

    def test_invalid_documents(self) -> None:
        for body in (b"", b"[]", b"not json", b"\xff\xfe", b'"text"'):
            assert parse_json_object(body) is None


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
