"""The workshop's scripted language model: assistant, autotest customer and judge."""

import json
import re

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.utilities.assembly.autotest_prompts import DONE_MARKER, JUDGE_SYSTEM_PROMPT
from app.utilities.llm_rehearsal.rehearsal_facts import find_fact_answer
from app.utilities.llm_rehearsal.rehearsal_reading import (
    last_customer_text as read_customer_words,
)
from app.utilities.memory.conversation_summary_prompt import (
    CONVERSATION_SUMMARY_SYSTEM_PROMPT,
)
from tests.e2e.harness_settings import JsonObject
from tests.e2e.model_script_texts import (
    ASSISTANT_TEXTS,
    BOOKING_WORDS,
    CUSTOMER_MESSAGES,
    GOAL_PATTERN,
    HANDOFF_WORDS,
    LANGUAGE_TAG_PATTERN,
    PRICE_WORDS,
    TRANSLITERATED_MESSAGES,
    TRANSLITERATION_MARKER,
    detect_language,
    read_customer_intent,
    read_reply_language,
)
from tests.e2e.model_script_turns import (
    call_tool,
    last_customer_text,
    last_tool_call,
    read_turn,
    read_turn_texts,
    say,
)


class WorkshopModelScript:
    """
    The scripted language model of the journey. It plays three roles, told
    apart by the request: the judge (judge prompt), the autotest customer
    (no tools) and the assistant (tools offered). The customer writes one
    message for its scenario goal in the scenario language; the assistant
    answers in the language the customer wrote in, books, quotes prices
    through get_price, hands off when asked for a manager and answers a
    question its fact table answers with that answer.
    """

    def __init__(self) -> None:
        self.assistant_calls: int = 0
        self.customer_calls: int = 0
        self.judge_calls: int = 0
        self.tool_calls: list[str] = []
        self.booking_request: JsonObject = {}

    def __call__(self, request: LlmRequest) -> ScriptedLlmTurn:
        if str(request.system_prompt) == JUDGE_SYSTEM_PROMPT:
            self.judge_calls += 1
            return say(
                json.dumps(
                    {
                        "scores": {
                            "facts_and_prices": 5,
                            "booking_data": 5,
                            "ai_disclosure": 5,
                            "handoff": 5,
                            "language": 5,
                        },
                        "notes": [],
                    }
                )
            )

        if str(request.system_prompt) == CONVERSATION_SUMMARY_SYSTEM_PROMPT:
            return say("The customer asked about a table and booked one.")

        if not request.tools:
            self.customer_calls += 1
            return self._play_customer(request)

        self.assistant_calls += 1
        language: str = read_reply_language(
            "\n".join(read_turn_texts(payload) for payload in request.transcript)
        ) or detect_language(last_customer_text(request))
        answered: tuple[str, JsonObject] | None = last_tool_call(request)
        if answered is not None:
            return self._after_tool(*answered, language=language)

        return self._answer(
            read_turn_texts(request.transcript[-1]),
            language,
            find_fact_answer(
                str(request.system_prompt), read_customer_words(request.transcript)
            ),
        )

    def _play_customer(self, request: LlmRequest) -> ScriptedLlmTurn:
        customer_turns: int = sum(
            1 for payload in request.transcript if read_turn(payload)["role"] == "user"
        )
        if customer_turns > 1:
            return say(DONE_MARKER)

        prompt: str = str(request.system_prompt)
        language_match: re.Match[str] | None = LANGUAGE_TAG_PATTERN.search(prompt)
        goal_match: re.Match[str] | None = GOAL_PATTERN.search(prompt)
        assert language_match is not None and goal_match is not None, prompt
        if TRANSLITERATION_MARKER in prompt:
            return say(TRANSLITERATED_MESSAGES[language_match.group(1)])

        return say(
            CUSTOMER_MESSAGES[language_match.group(1)][
                read_customer_intent(goal_match.group(1))
            ]
        )

    def _answer(
        self, customer_text: str, language: str, known_answer: str | None
    ) -> ScriptedLlmTurn:
        if any(word in customer_text for word in HANDOFF_WORDS):
            return self._call(
                AssistantToolName.HANDOFF_TO_HUMAN,
                {
                    "reason": "customer_request",
                    "summary": "The customer asks for a manager.",
                    "urgency": "normal",
                },
            )

        if any(word in customer_text for word in BOOKING_WORDS):
            return self._call(
                AssistantToolName.CHECK_AVAILABILITY,
                {
                    "resource_type": None,
                    "date": "2026-10-06",
                    "time": "19:00",
                    "party_size": 2,
                    "duration_minutes": None,
                    "nights": None,
                },
            )

        if any(word in customer_text for word in PRICE_WORDS):
            return self._call(AssistantToolName.GET_PRICE, {"item_name": "ხაჭაპური"})

        if known_answer is not None:
            return say(known_answer)

        return say(ASSISTANT_TEXTS[language]["greeting"])

    def _after_tool(
        self,
        tool_name: str,
        result: JsonObject,
        language: str,
    ) -> ScriptedLlmTurn:
        texts: dict[str, str] = ASSISTANT_TEXTS[language]
        if tool_name == AssistantToolName.CHECK_AVAILABILITY:
            self.booking_request = {
                "name": "Нино",
                "phone": "+995 555 12 34 56",
                "resource_type": None,
                "date": "2026-10-06",
                "time": "19:00",
                "party_size": 2,
                "duration_minutes": None,
                "nights": None,
                "notes": "У окна",
            }
            return self._call(AssistantToolName.CREATE_BOOKING, self.booking_request)

        if tool_name == AssistantToolName.CREATE_BOOKING:
            return say(texts["booked"])

        if tool_name == AssistantToolName.GET_PRICE:
            matches: list[JsonObject] = result["matches"]
            if not matches:
                return say(texts["no_price"])

            return say(texts["price"].format(price=matches[0]["price_text"]))

        if tool_name == AssistantToolName.HANDOFF_TO_HUMAN:
            return say(str(result["customer_message"]))

        return say(texts["fine"])

    def _call(
        self, tool_name: AssistantToolName, arguments: JsonObject
    ) -> ScriptedLlmTurn:
        self.tool_calls.append(tool_name.value)
        return call_tool(tool_name, arguments)
