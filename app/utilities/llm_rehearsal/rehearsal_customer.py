"""
The AI customer of the rehearsal model (LLM_PROVIDER=scripted): one
sentence for its scenario goal in the scenario language (the item it asks
the price of in quotes, its phone number when it books), then [DONE].
"""

from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.assembly.autotest_prompts import (
    DONE_MARKER,
    OWNER_CHECK_CONTINUATION_OPENING,
    TRANSLITERATION_NOTE,
)
from app.utilities.llm_rehearsal.assistant_phrases import FALLBACK_LANGUAGE
from app.utilities.llm_rehearsal.customer_phrases import (
    CUSTOMER_PHRASES,
    TRANSLITERATED_PHRASES,
    RehearsalIntent,
)
from app.utilities.llm_rehearsal.rehearsal_reading import (
    read_customer_goal,
    read_goal_item,
    read_texts,
    read_turn,
)


def play_customer(request: LlmRequest) -> ScriptedLlmTurn:
    if any(
        read_turn(payload).get("role") == "assistant"
        or OWNER_CHECK_CONTINUATION_OPENING in read_texts(payload)
        for payload in request.transcript
    ):
        return say(DONE_MARKER)

    language, intent, phone = read_customer_goal(str(request.system_prompt))
    item: str | None = read_goal_item(str(request.system_prompt))
    base_language: str = language.split("-")[0].lower()
    if TRANSLITERATION_NOTE in str(request.system_prompt) and (
        base_language in TRANSLITERATED_PHRASES
    ):
        return say(TRANSLITERATED_PHRASES[base_language])

    phrases = CUSTOMER_PHRASES.get(base_language) or CUSTOMER_PHRASES[FALLBACK_LANGUAGE]
    if intent is RehearsalIntent.BOOKING and phone is not None:
        return say(f"{phrases[intent]} {phone}")

    if intent is RehearsalIntent.PRICE and item is not None:
        # The greeting after the item keeps the scenario language the one
        # the platform reads, whatever script the item's title is in.
        return say(f'{phrases[intent]} "{item}" {phrases[RehearsalIntent.OTHER]}')

    return say(phrases[intent])


def say(text: str) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(text=MessageText(text))
