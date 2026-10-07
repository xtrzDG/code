"""
How offered options read as text and as each platform's JSON, and how a
reply is split so its last part can carry them.
"""

import pytest

from app.schemas.constants.channels import InboundContextNote
from app.schemas.domain.reply_choices import ReplyChoices
from app.schemas.typings.conversations.constrained_strings import (
    ChoiceLabel,
    ChoicePromptText,
)
from app.utilities.channels.choice_delivery import split_reply
from app.utilities.channels.choice_payloads import (
    TELEGRAM_CALLBACK_DATA_BYTES,
    fallback_room,
    page_quick_replies,
    row_width,
    telegram_callback_data,
    telegram_inline_keyboard,
    whatsapp_body_limit,
)
from app.utilities.channels.meta_story_context import read_story_note
from app.utilities.conversations.reply_choices_text import (
    close_with_prompt,
    number_the_options,
    text_with_options,
)

YES_NO: ReplyChoices = ReplyChoices(
    prompt=ChoicePromptText("Shall I book it?"),
    options=[ChoiceLabel("Yes"), ChoiceLabel("No")],
)


def choices(*options: str) -> ReplyChoices:
    return ReplyChoices(
        prompt=ChoicePromptText("Which one?"),
        options=[ChoiceLabel(option) for option in options],
    )


class TestText:
    def test_the_prompt_closes_the_reply_once(self) -> None:
        assert close_with_prompt("A table for 2.", YES_NO) == (
            "A table for 2.\n\nShall I book it?"
        )
        # The model repeated the question despite the note: not twice.
        assert close_with_prompt("A table for 2.\nShall I book it", YES_NO) == (
            "A table for 2.\nShall I book it"
        )
        assert close_with_prompt("", YES_NO) == "Shall I book it?"
        assert close_with_prompt("No options.", None) == "No options."

    def test_the_fallback_numbers_the_options(self) -> None:
        assert number_the_options("Shall I book it?", YES_NO) == (
            "Shall I book it?\n\n1. Yes\n2. No"
        )

    def test_the_guard_reads_the_options_without_numbers(self) -> None:
        assert text_with_options("A table for 2.", YES_NO) == (
            "A table for 2.\n\nShall I book it?\n\nYes\nNo"
        )
        assert text_with_options("Plain.", None) == "Plain."

    @pytest.mark.parametrize(
        "label",
        ["", " Yes", "Yes ", "Line\nbreak", "A label of 21 letters"],
    )
    def test_labels_are_short_single_lines(self, label: str) -> None:
        with pytest.raises(ValueError):
            ChoiceLabel(label)


class TestPayloads:
    def test_telegram_rows_follow_the_longest_label(self) -> None:
        assert row_width(5) == 3
        assert row_width(8) == 3
        assert row_width(9) == 2
        assert row_width(14) == 2
        assert row_width(15) == 1
        keyboard = telegram_inline_keyboard(choices("Table by the window", "Bar"))
        assert keyboard == {
            "inline_keyboard": [
                [
                    {
                        "text": "Table by the window",
                        "callback_data": "Table by the window",
                    }
                ],
                [{"text": "Bar", "callback_data": "Bar"}],
            ]
        }

    def test_an_option_too_long_for_callback_data_rides_by_number(self) -> None:
        emoji_option = "🍷" * 17
        assert len(emoji_option.encode()) > TELEGRAM_CALLBACK_DATA_BYTES
        assert telegram_callback_data(2, emoji_option) == "#2"
        assert telegram_callback_data(1, "19:30") == "19:30"

    def test_quick_replies_send_the_title_back(self) -> None:
        assert page_quick_replies(YES_NO) == [
            {"content_type": "text", "title": "Yes", "payload": "choice-1"},
            {"content_type": "text", "title": "No", "payload": "choice-2"},
        ]

    def test_whatsapp_bodies_are_shorter_for_buttons_than_for_lists(self) -> None:
        assert whatsapp_body_limit(choices("1", "2", "3")) == 1024
        assert whatsapp_body_limit(choices("1", "2", "3", "4")) == 4096


class TestSplitting:
    def test_parts_leave_room_for_the_numbered_list(self) -> None:
        text = ("word " * 900).strip()
        offer = choices("18:00", "19:30")

        parts = split_reply(text, 4096, offer)

        room = fallback_room(offer)
        assert room == len("\n\n1. 18:00\n2. 19:30")
        assert all(len(part) <= 4096 - room for part in parts)
        assert " ".join(parts) == text
        # The last part fits whole, so splitting it again keeps it as it is.
        assert split_reply(parts[-1], 4096, offer) == [parts[-1]]

    def test_a_platform_limit_for_messages_with_buttons_applies_too(self) -> None:
        parts = split_reply("x " * 800, 4096, YES_NO, choice_limit=1024)

        assert all(len(part) <= 1024 for part in parts)

    def test_without_options_the_channel_limit_alone_counts(self) -> None:
        assert split_reply("short", 4096, None) == ["short"]


class TestStoryContext:
    def test_a_story_reply_and_a_story_mention(self) -> None:
        reply: dict[str, object] = {
            "mid": "m",
            "text": "Hi",
            "reply_to": {"story": {"id": "1", "url": "u"}},
        }
        mention: dict[str, object] = {
            "mid": "m",
            "attachments": [{"type": "story_mention", "payload": {}}],
        }
        plain: dict[str, object] = {"mid": "m", "text": "Hi", "reply_to": {"mid": "m0"}}

        assert read_story_note(reply) is InboundContextNote.STORY_REPLY
        assert read_story_note(mention) is InboundContextNote.STORY_MENTION
        assert read_story_note(plain) is None
