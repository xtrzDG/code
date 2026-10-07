"""
The injection detector: whether a customer's message looks like a
prompt-injection attempt, and of which kind. A heuristic, not a verdict:
a flagged message is still answered (the model reads customer text inside
a fence it cannot forge); the flag is stored on the message, counted in
the admin's client health, and a contact who keeps sending such messages
is stopped for a day (`turn_gate`).
"""

import re
import unicodedata
from functools import cache

from app.schemas.constants.reply_safety import InjectionSignal
from app.utilities.conversations.customer_text_fencing import (
    INVISIBLE_CHARACTERS,
    imitates_platform,
)
from app.utilities.reply_guard.injection_markers import (
    FAKE_PLATFORM_PATTERNS,
    compile_patterns,
)

MAX_CHECKED_CHARACTERS: int = 4000
SPACES_PATTERN: re.Pattern[str] = re.compile(r"[ \t ]+")
# Checked in this order; the first kind that matches names the attempt.
SIGNAL_ORDER: tuple[InjectionSignal, ...] = (
    InjectionSignal.INSTRUCTION_OVERRIDE,
    InjectionSignal.PROMPT_EXTRACTION,
    InjectionSignal.DATA_EXFILTRATION,
    InjectionSignal.ROLE_CHANGE,
)


def detect_injection(text: str) -> InjectionSignal | None:
    """The kind of injection attempt the text looks like; None for none."""

    if any(imitates_platform(line) for line in text.split("\n")):
        return InjectionSignal.FAKE_PLATFORM_TEXT

    folded: str = fold_text(text[:MAX_CHECKED_CHARACTERS])
    if any(pattern.search(folded) for pattern in fake_platform_patterns()):
        return InjectionSignal.FAKE_PLATFORM_TEXT

    for signal in SIGNAL_ORDER:
        if any(pattern.search(folded) for pattern in signal_patterns(signal)):
            return signal

    return None


def fold_text(text: str) -> str:
    """Compatibility forms, lower case, no invisible characters, one space."""

    normalized: str = unicodedata.normalize("NFKC", text).lower()
    visible: str = "".join(
        character for character in normalized if character not in INVISIBLE_CHARACTERS
    )
    return SPACES_PATTERN.sub(" ", visible)


@cache
def fake_platform_patterns() -> tuple[re.Pattern[str], ...]:
    return tuple(
        re.compile(pattern, re.MULTILINE) for pattern in FAKE_PLATFORM_PATTERNS
    )


@cache
def signal_patterns(signal: InjectionSignal) -> tuple[re.Pattern[str], ...]:
    return compile_patterns(signal)
