"""Reading the customer's fenced words back out of a user turn."""

import re

FENCE_PATTERN: re.Pattern[str] = re.compile(
    r"<customer_text (?P<key>[0-9a-f]{8})>\n(?P<text>.*?)\n</customer_text (?P=key)>",
    re.DOTALL,
)


def fenced_texts(turn: str) -> list[str]:
    """Every fenced customer text of the turn, in order."""

    return [match.group("text") for match in FENCE_PATTERN.finditer(turn)]


def ends_with_fenced(turn: str, text: str) -> bool:
    """The turn ends with `text` as the customer's fenced latest message."""

    matches = list(FENCE_PATTERN.finditer(turn))
    return (
        bool(matches)
        and matches[-1].end() == len(turn.rstrip())
        and matches[-1].group("text") == text
    )
