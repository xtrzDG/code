"""
The offered options as each platform shows them (the JSON parts of a send),
and the room a reply's text leaves for them.

- WhatsApp: up to 3 reply buttons on a message of at most 1024 characters,
  else a list of up to 10 rows behind one button (body up to 4096).
- Telegram: an inline keyboard; a tap sends a callback whose data is the
  option itself, or `#<n>` when the option is longer than Telegram's 64
  bytes of callback data (read back from the keyboard of the message).
- Messenger and Instagram: quick replies under the message.

Every channel keeps room in a reply's last part for the numbered list it
falls back to when the platform refuses the buttons.
"""

from app.schemas.domain.reply_choices import ReplyChoices
from app.utilities.channels.json_values import JsonObject
from app.utilities.conversations.reply_choices_text import (
    PARAGRAPH_BREAK,
    number_the_options,
)

WHATSAPP_BUTTON_LIMIT: int = 3
WHATSAPP_BUTTON_BODY_LIMIT: int = 1024
WHATSAPP_LIST_BODY_LIMIT: int = 4096
CHOICE_ID_PREFIX: str = "choice-"
TELEGRAM_CALLBACK_DATA_BYTES: int = 64
TELEGRAM_INDEX_PREFIX: str = "#"
# Options per keyboard row by the longest option: short times go three in
# a row, longer labels two, sentences one.
TELEGRAM_ROW_WIDTHS: tuple[tuple[int, int], ...] = ((8, 3), (14, 2))


def fallback_room(choices: ReplyChoices | None) -> int:
    """The characters a numbered list of the options adds to a text."""

    if choices is None:
        return 0

    return len(number_the_options("", choices)) + len(PARAGRAPH_BREAK)


def whatsapp_body_limit(choices: ReplyChoices) -> int:
    return (
        WHATSAPP_BUTTON_BODY_LIMIT
        if len(choices.options) <= WHATSAPP_BUTTON_LIMIT
        else WHATSAPP_LIST_BODY_LIMIT
    )


def whatsapp_interactive(
    body: str, choices: ReplyChoices, list_button: str
) -> JsonObject:
    """Reply buttons for up to three options, a list for more."""

    if len(choices.options) <= WHATSAPP_BUTTON_LIMIT:
        return {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": choice_id(index), "title": str(option)},
                    }
                    for index, option in enumerate(choices.options, start=1)
                ]
            },
        }

    return {
        "type": "list",
        "body": {"text": body},
        "action": {
            "button": list_button,
            "sections": [
                {
                    "rows": [
                        {"id": choice_id(index), "title": str(option)}
                        for index, option in enumerate(choices.options, start=1)
                    ]
                }
            ],
        },
    }


def page_quick_replies(choices: ReplyChoices) -> list[JsonObject]:
    """Messenger and Instagram quick replies; a tap sends the title as text."""

    return [
        {"content_type": "text", "title": str(option), "payload": choice_id(index)}
        for index, option in enumerate(choices.options, start=1)
    ]


def telegram_inline_keyboard(choices: ReplyChoices) -> JsonObject:
    """An inline keyboard of the options, rows as wide as the labels allow."""

    buttons: list[JsonObject] = [
        {
            "text": str(option),
            "callback_data": telegram_callback_data(index, str(option)),
        }
        for index, option in enumerate(choices.options, start=1)
    ]
    width: int = row_width(max(len(str(option)) for option in choices.options))
    return {
        "inline_keyboard": [
            buttons[start : start + width] for start in range(0, len(buttons), width)
        ]
    }


def telegram_callback_data(index: int, option: str) -> str:
    if len(option.encode()) <= TELEGRAM_CALLBACK_DATA_BYTES:
        return option

    return f"{TELEGRAM_INDEX_PREFIX}{index}"


def row_width(longest: int) -> int:
    for limit, width in TELEGRAM_ROW_WIDTHS:
        if longest <= limit:
            return width

    return 1


def choice_id(index: int) -> str:
    return f"{CHOICE_ID_PREFIX}{index}"
