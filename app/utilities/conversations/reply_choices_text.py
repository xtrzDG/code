"""
How a reply that offers choices reads as text: its prompt closes the
reply, and where a channel cannot show buttons the options follow as a
numbered list (the customer answers with the option or its number).
"""

import re

from app.schemas.domain.reply_choices import ReplyChoices

PARAGRAPH_BREAK: str = "\n\n"
# Ignored when comparing a reply's last line with the prompt.
TRAILING_MARKS: re.Pattern[str] = re.compile(r"[\s.!?…:;,؟。！？]+$")


def close_with_prompt(text: str, choices: ReplyChoices | None) -> str:
    """
    The reply followed by the choices' prompt, unless its last line already
    asks the same (the model was told not to repeat it, but may).
    """

    if choices is None:
        return text

    prompt: str = str(choices.prompt)
    last_line: str = text.rstrip().rsplit("\n", 1)[-1]
    if comparable(last_line) == comparable(prompt) or not text.strip():
        return text if text.strip() else prompt

    return f"{text.rstrip()}{PARAGRAPH_BREAK}{prompt}"


def number_the_options(text: str, choices: ReplyChoices) -> str:
    """The text with the options as a numbered list after it ("1. 18:00")."""

    options: str = "\n".join(
        f"{position}. {option}"
        for position, option in enumerate(choices.options, start=1)
    )
    return f"{text.rstrip()}{PARAGRAPH_BREAK}{options}"


def text_with_options(text: str, choices: ReplyChoices | None) -> str:
    """
    Everything the customer will read: the text, the prompt and the
    options, one per line without numbers (what the reply guard checks:
    the numbers of a fallback list are the platform's, not claims).
    """

    if choices is None:
        return text

    options: str = "\n".join(str(option) for option in choices.options)
    return f"{close_with_prompt(text, choices)}{PARAGRAPH_BREAK}{options}"


def comparable(line: str) -> str:
    return TRAILING_MARKS.sub("", line.strip()).casefold()
