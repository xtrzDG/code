"""
Reading what the rehearsal model (LLM_PROVIDER=scripted) is asked: the
transcript's turns, the customer's own words, their language, and the
AI customer's instruction.
"""

import json
import re
from collections.abc import Sequence
from typing import cast

from app.schemas.typings.localization.constrained_strings import ScriptCode
from app.utilities.assembly.script_detection import is_written_in_script
from app.utilities.conversations.customer_text_fencing import FENCE_TAG
from app.utilities.conversations.turn_context import CUSTOMER_HEADER
from app.utilities.llm_rehearsal.assistant_phrases import FALLBACK_LANGUAGE
from app.utilities.llm_rehearsal.customer_phrases import (
    CUSTOMER_PHRASES,
    RehearsalIntent,
)

type JsonObject = dict[str, object]

LANGUAGE_TAG_PATTERN: re.Pattern[str] = re.compile(r"language tag ([A-Za-z\-]+)\)")
REPLY_LANGUAGE_PATTERN: re.Pattern[str] = re.compile(
    r"^Reply language: .*\(([a-z]{2,3}(?:-[A-Za-z0-9]+)*)\)\.", re.MULTILINE
)
GOAL_PATTERN: re.Pattern[str] = re.compile(r"^Your goal: (.+)$", re.MULTILINE)
PHONE_LINE_PATTERN: re.Pattern[str] = re.compile(r"Your phone number is ([+\d][\d ]+)")
PHONE_PATTERN: re.Pattern[str] = re.compile(r"\+\d[\d \-]{6,}\d")
NEXT_DAYS_PATTERN: re.Pattern[str] = re.compile(r"^Next days: (.+)\.$", re.MULTILINE)
ISO_DATE_PATTERN: re.Pattern[str] = re.compile(r"\d{4}-\d{2}-\d{2}")
FENCED_TEXT_PATTERN: re.Pattern[str] = re.compile(
    rf"<{FENCE_TAG} [^>]*>\n(.*?)\n</{FENCE_TAG} [^>]*>", re.DOTALL
)
# A script that is not Latin tells the language; Cyrillic and Latin need
# the rehearsal's own sentences to tell their languages apart.
LANGUAGES_BY_SCRIPT: tuple[tuple[str, str], ...] = (
    ("Geor", "ka"),
    ("Hebr", "he"),
    ("Arab", "ar"),
    ("Armn", "hy"),
    ("Grek", "el"),
    ("Cyrl", "ru"),
)


def read_turn(payload: str) -> JsonObject:
    return cast(JsonObject, json.loads(payload))


def read_blocks(payload: str) -> list[JsonObject]:
    content: object = read_turn(payload).get("content", [])
    return cast(list[JsonObject], content) if isinstance(content, list) else []


def read_texts(payload: str) -> str:
    return "\n".join(
        str(block.get("text", ""))
        for block in read_blocks(payload)
        if block.get("type") == "text"
    )


def last_customer_text(transcript: Sequence[str]) -> str:
    """The customer's own words in the latest user turn that has text."""

    for payload in reversed(transcript):
        if read_turn(payload).get("role") != "user":
            continue

        text: str = read_texts(payload)
        if text:
            _, header, words = text.partition(CUSTOMER_HEADER)
            fenced: list[str] = FENCED_TEXT_PATTERN.findall(words if header else text)
            return fenced[-1] if fenced else (words if header else text).strip()

    return ""


def read_reply_language(transcript: Sequence[str]) -> str | None:
    """The language the platform read the customer's latest message in."""

    for payload in reversed(transcript):
        if read_turn(payload).get("role") != "user":
            continue

        match: re.Match[str] | None = REPLY_LANGUAGE_PATTERN.search(read_texts(payload))
        if match is not None:
            return match.group(1)

    return None


def next_days(transcript: Sequence[str]) -> list[str]:
    """The dates of "Next days: ..." in the latest platform context."""

    for payload in reversed(transcript):
        match: re.Match[str] | None = NEXT_DAYS_PATTERN.search(read_texts(payload))
        if match is not None:
            return ISO_DATE_PATTERN.findall(match.group(1))

    return []


def find_phone(text: str) -> str | None:
    match: re.Match[str] | None = PHONE_PATTERN.search(text)
    return None if match is None else re.sub(r"[ \-]", "", match.group(0))


def detect_language(text: str) -> str:
    """The language of the customer's words, as far as the rehearsal can tell."""

    for language, phrases in CUSTOMER_PHRASES.items():
        if any(text.strip().startswith(phrase) for phrase in phrases.values()):
            return language

    for script, language in LANGUAGES_BY_SCRIPT:
        if is_written_in_script(text, ScriptCode(script)):
            return language

    return FALLBACK_LANGUAGE


def read_customer_goal(system_prompt: str) -> tuple[str, RehearsalIntent, str | None]:
    """
    The AI customer's language tag, intent and phone number, read from its
    instruction (see `build_customer_persona_prompt`).
    """

    language_match: re.Match[str] | None = LANGUAGE_TAG_PATTERN.search(system_prompt)
    goal_match: re.Match[str] | None = GOAL_PATTERN.search(system_prompt)
    phone_match: re.Match[str] | None = PHONE_LINE_PATTERN.search(system_prompt)
    language: str = (
        FALLBACK_LANGUAGE if language_match is None else language_match.group(1)
    )
    goal: str = "" if goal_match is None else goal_match.group(1)
    phone: str | None = (
        None if phone_match is None else re.sub(r"\s", "", phone_match.group(1))
    )
    return language, read_goal_intent(goal), phone


def read_goal_intent(goal: str) -> RehearsalIntent:
    if goal.startswith("Book a "):
        return RehearsalIntent.BOOKING

    if goal.startswith("Ask how much"):
        return RehearsalIntent.PRICE

    if goal.startswith("Ask to talk to a human"):
        return RehearsalIntent.PERSON

    if goal.startswith("Report an emergency"):
        return RehearsalIntent.EMERGENCY

    return RehearsalIntent.OTHER
