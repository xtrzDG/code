"""
The team's notes are context, never words for the customer.

A returning customer's memory gives the model the team's internal notes on
them (`<team_note>` blocks of the context line, `untrusted_text`), so it can
serve them better ("prefers the window table"). A reply that writes
QUOTED_RUN_WORDS words of a note in a row (ignoring case and punctuation)
quotes it, and the guard holds it back: a few words in common ("the table
by the window") stay fine.
"""

import json
import re
from collections.abc import Iterable, Sequence
from typing import cast

from app.utilities.conversations.untrusted_text import TEAM_NOTE_TAG, find_team_notes

QUOTED_RUN_WORDS: int = 5
WORD_PATTERN: re.Pattern[str] = re.compile(r"\w+")

type WordRun = tuple[str, ...]


def find_quoted_notes(reply_text: str, notes: Sequence[str]) -> list[str]:
    """The notes the reply quotes, each once, in their order."""

    written: set[WordRun] = word_runs(reply_text)
    if not written:
        return []

    return [note for note in dict.fromkeys(notes) if word_runs(note) & written]


def word_runs(text: str) -> set[WordRun]:
    """Every QUOTED_RUN_WORDS words in a row of the text, case-folded."""

    words: list[str] = [word.casefold() for word in WORD_PATTERN.findall(text)]
    return {
        tuple(words[start : start + QUOTED_RUN_WORDS])
        for start in range(len(words) - QUOTED_RUN_WORDS + 1)
    }


def find_transcript_notes(payloads: Iterable[str]) -> list[str]:
    """
    The team notes the model was shown in a conversation: the note blocks
    of every stored turn (provider payloads are JSON, read as such so an
    escaped letter still reads as itself).
    """

    notes: list[str] = []
    for payload in payloads:
        if TEAM_NOTE_TAG not in payload:
            continue

        for text in payload_texts(payload):
            notes.extend(find_team_notes(text))

    return notes


def payload_texts(payload: str) -> list[str]:
    """Every string of a JSON payload; the payload itself when it is no JSON."""

    try:
        decoded: object = json.loads(payload)
    except ValueError:
        return [payload]

    return list(strings_of(decoded))


def strings_of(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in cast(dict[object, object], value).values():
            yield from strings_of(item)
    elif isinstance(value, list):
        for item in cast(list[object], value):
            yield from strings_of(item)
