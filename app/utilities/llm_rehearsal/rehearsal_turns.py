"""
The rehearsal model of LLM_PROVIDER=scripted: without a language model it
plays the three roles of the automatic checks so they can pass on a
development, staging or end-to-end server, and stays a plain test
assistant in every other chat.

- The judge (the judge's instruction) scores every criterion 5: nothing is
  judged, so only the checks of what the assistant did (a booking made, a
  conversation passed to a person, the reply's script) can fail.
- The AI customer (its instruction) says one sentence for its goal in the
  scenario language, with its phone number when it books, then [DONE].
- The topic grouping (its instruction) puts what customers asked into
  topics by keywords (`rehearsal_topics.py`).
- The assistant (anything else) answers a question of its fact table with
  that answer (`rehearsal_facts.py`), else in the customer's language: it
  books the first free time of the next days when asked to book, passes
  the conversation to a colleague when asked for a person or in an
  emergency, and otherwise says that it is a test assistant.
"""

import json
from collections.abc import Sequence
from typing import cast

from app.schemas.constants.assistants import AssistantToolName, JudgeCriterion
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.typings.conversations.strings import LlmToolInputJson, MessageText
from app.utilities.assembly.autotest_prompts import (
    CUSTOMER_PERSONA_OPENING,
    DONE_MARKER,
    JUDGE_SYSTEM_PROMPT,
    OWNER_CHECK_CONTINUATION_OPENING,
    TRANSLITERATION_NOTE,
)
from app.utilities.llm_rehearsal.assistant_phrases import (
    ASSISTANT_PHRASES,
    CUSTOMER_NAMES,
    FALLBACK_LANGUAGE,
    RehearsalReply,
)
from app.utilities.llm_rehearsal.customer_phrases import (
    BOOKING_KEYWORDS,
    CUSTOMER_PHRASES,
    PERSON_KEYWORDS,
    TRANSLITERATED_PHRASES,
    RehearsalIntent,
)
from app.utilities.llm_rehearsal.rehearsal_facts import find_fact_answer
from app.utilities.llm_rehearsal.rehearsal_reading import (
    JsonObject,
    detect_language,
    find_phone,
    last_customer_text,
    next_days,
    read_blocks,
    read_customer_goal,
    read_reply_language,
    read_texts,
    read_turn,
)
from app.utilities.llm_rehearsal.rehearsal_topics import rehearse_topics
from app.utilities.value.topic_grouping import TOPIC_SYSTEM_PROMPT

PERFECT_SCORE: int = 5
REHEARSAL_PARTY_SIZE: int = 1
HANDOFF_INTENTS: frozenset[RehearsalIntent] = frozenset(
    {RehearsalIntent.PERSON, RehearsalIntent.EMERGENCY}
)


def play_rehearsal_turn(request: LlmRequest) -> ScriptedLlmTurn:
    """The rehearsal's answer to one request, by the role it plays."""

    if str(request.system_prompt) == JUDGE_SYSTEM_PROMPT:
        return say(
            json.dumps(
                {
                    "scores": {
                        criterion.value: PERFECT_SCORE for criterion in JudgeCriterion
                    },
                    "notes": [],
                }
            )
        )

    if str(request.system_prompt).startswith(CUSTOMER_PERSONA_OPENING):
        return play_customer(request)

    if str(request.system_prompt) == TOPIC_SYSTEM_PROMPT:
        return say(rehearse_topics(read_texts(request.transcript[-1])))

    return play_assistant(request)


def play_customer(request: LlmRequest) -> ScriptedLlmTurn:
    if any(
        read_turn(payload).get("role") == "assistant"
        or OWNER_CHECK_CONTINUATION_OPENING in read_texts(payload)
        for payload in request.transcript
    ):
        return say(DONE_MARKER)

    language, intent, phone = read_customer_goal(str(request.system_prompt))
    base_language: str = language.split("-")[0].lower()
    if TRANSLITERATION_NOTE in str(request.system_prompt) and (
        base_language in TRANSLITERATED_PHRASES
    ):
        return say(TRANSLITERATED_PHRASES[base_language])

    phrases = CUSTOMER_PHRASES.get(base_language) or CUSTOMER_PHRASES[FALLBACK_LANGUAGE]
    if intent is RehearsalIntent.BOOKING and phone is not None:
        return say(f"{phrases[intent]} {phone}")

    return say(phrases[intent])


def play_assistant(request: LlmRequest) -> ScriptedLlmTurn:
    customer_text: str = last_customer_text(request.transcript)
    # The platform's reading of the customer's language, as a model gets it.
    language: str = (
        read_reply_language(request.transcript) or detect_language(customer_text)
    ).split("-")[0]
    tool_names: set[str] = {str(tool.name) for tool in request.tools}
    answered: tuple[JsonObject, JsonObject] | None = last_tool_exchange(
        request.transcript
    )
    if answered is not None:
        return after_tool(request.transcript, *answered, language=language)

    known: str | None = find_fact_answer(str(request.system_prompt), customer_text)
    if known is not None:
        return say(known)

    intent: RehearsalIntent = read_intent(customer_text)
    if intent in HANDOFF_INTENTS and AssistantToolName.HANDOFF_TO_HUMAN in tool_names:
        return call(
            AssistantToolName.HANDOFF_TO_HUMAN,
            {
                "reason": (
                    HandoffReason.EMERGENCY
                    if intent is RehearsalIntent.EMERGENCY
                    else HandoffReason.CUSTOMER_REQUEST
                ),
                "summary": "The customer asks for a person.",
                "urgency": (
                    HandoffUrgency.CRITICAL
                    if intent is RehearsalIntent.EMERGENCY
                    else HandoffUrgency.NORMAL
                ),
            },
        )

    days: list[str] = next_days(request.transcript)
    if (
        intent is RehearsalIntent.BOOKING
        and AssistantToolName.CHECK_AVAILABILITY in tool_names
        and days
    ):
        return check_availability(days[0])

    return say(reply_text(language, RehearsalReply.ANSWER))


def read_intent(customer_text: str) -> RehearsalIntent:
    text: str = customer_text.strip()
    for phrases in CUSTOMER_PHRASES.values():
        for intent, phrase in phrases.items():
            if text.startswith(phrase):
                return intent

    lowered: str = text.casefold()
    if any(keyword in lowered for keyword in PERSON_KEYWORDS):
        return RehearsalIntent.PERSON

    if any(keyword in lowered for keyword in BOOKING_KEYWORDS):
        return RehearsalIntent.BOOKING

    return RehearsalIntent.OTHER


def after_tool(
    transcript: Sequence[str],
    call_block: JsonObject,
    result: JsonObject,
    language: str,
) -> ScriptedLlmTurn:
    name: str = str(call_block.get("name", ""))
    arguments: object = call_block.get("input", {})
    if name == AssistantToolName.CHECK_AVAILABILITY and isinstance(arguments, dict):
        return book_or_look_further(
            transcript, cast(JsonObject, arguments), result, language
        )

    if name == AssistantToolName.CREATE_BOOKING:
        return say(
            reply_text(
                language,
                RehearsalReply.NO_TIME if "error" in result else RehearsalReply.BOOKED,
            )
        )

    if name == AssistantToolName.HANDOFF_TO_HUMAN and "customer_message" in result:
        return say(str(result["customer_message"]))

    return say(reply_text(language, RehearsalReply.PASSED_ON))


def book_or_look_further(
    transcript: Sequence[str],
    arguments: JsonObject,
    result: JsonObject,
    language: str,
) -> ScriptedLlmTurn:
    """Book the first free slot, or ask about the next day."""

    slots: object = result.get("slots", [])
    if isinstance(slots, list) and slots and isinstance(slots[0], dict):
        slot: JsonObject = cast(JsonObject, slots[0])
        return call(
            AssistantToolName.CREATE_BOOKING,
            {
                "name": CUSTOMER_NAMES.get(language, CUSTOMER_NAMES[FALLBACK_LANGUAGE]),
                "phone": find_phone(last_customer_text(transcript)),
                "date": slot.get("date"),
                "time": slot.get("time"),
                "nights": slot.get("nights"),
                "duration_minutes": slot.get("duration_minutes"),
                "party_size": REHEARSAL_PARTY_SIZE,
            },
        )

    days: list[str] = next_days(transcript)
    tried: str = str(arguments.get("date", ""))
    later: list[str] = days[days.index(tried) + 1 :] if tried in days else []
    if later:
        return check_availability(later[0])

    return say(reply_text(language, RehearsalReply.NO_TIME))


def last_tool_exchange(
    transcript: Sequence[str],
) -> tuple[JsonObject, JsonObject] | None:
    """The tool call answered by the latest turn and its result, if it is one."""

    if len(transcript) < 2:
        return None

    results: list[JsonObject] = [
        block
        for block in read_blocks(transcript[-1])
        if block.get("type") == "tool_result"
    ]
    calls: list[JsonObject] = [
        block
        for block in read_blocks(transcript[-2])
        if block.get("type") == "tool_use"
    ]
    if not results or not calls:
        return None

    try:
        parsed: object = json.loads(str(results[-1].get("content", "")))
    except json.JSONDecodeError:
        parsed = {}

    result: JsonObject = cast(JsonObject, parsed) if isinstance(parsed, dict) else {}
    if results[-1].get("is_error"):
        return calls[-1], {"error": result}

    return calls[-1], result


def check_availability(date: str) -> ScriptedLlmTurn:
    return call(
        AssistantToolName.CHECK_AVAILABILITY,
        {"date": date, "party_size": REHEARSAL_PARTY_SIZE},
    )


def reply_text(language: str, reply: RehearsalReply) -> str:
    phrases = ASSISTANT_PHRASES.get(language) or ASSISTANT_PHRASES[FALLBACK_LANGUAGE]
    return phrases[reply]


def say(text: str) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(text=MessageText(text))


def call(tool_name: AssistantToolName, arguments: JsonObject) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(
        tool_calls=[
            ScriptedToolCall(
                tool_name=tool_name,
                input_json=LlmToolInputJson(json.dumps(arguments, ensure_ascii=False)),
            )
        ]
    )
