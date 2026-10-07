"""
Whether a customer's message reads as finished: a sentence longer than a
fragment that ends with a full stop, a question or an exclamation mark (in
Latin, Cyrillic, Georgian and the other scripts' own forms). Such a message
is answered at once; a fragment ("Hi", "for 4 people", "and also...")
waits a moment for the rest of what the customer is writing.
"""

from app.schemas.typings.conversations.strings import MessageText

# A message this long or shorter is a fragment, whatever it ends with
# ("Hi!", "Ok.", "Tomorrow?").
FRAGMENT_MAX_LENGTH: int = 12
# Full stop, question and exclamation marks: ASCII, full-width (CJK),
# Arabic, Armenian and Devanagari.
SENTENCE_ENDINGS: frozenset[str] = frozenset(".?!。？！؟։।")
# Trailing dots say the customer is not done.
CONTINUATION_ENDINGS: tuple[str, ...] = ("..", "…")
# Closing brackets and quotes after the mark ("Is parking free?)") and the
# whitespace around them.
TRAILING_CLOSERS: str = ")]}\"'»”’ \t\r\n"


def is_complete_message(text: MessageText) -> bool:
    """A finished sentence, longer than FRAGMENT_MAX_LENGTH characters."""

    written: str = str(text).strip()
    if len(written) <= FRAGMENT_MAX_LENGTH:
        return False

    ending: str = written.rstrip(TRAILING_CLOSERS)
    if ending.endswith(CONTINUATION_ENDINGS):
        return False

    return ending[-1:] in SENTENCE_ENDINGS
