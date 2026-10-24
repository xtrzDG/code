"""
The rehearsal model of LLM_PROVIDER=scripted plays the three roles of the
automatic checks: the judge, the AI customer and the assistant, in the
customer's language.
"""

import json

from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_text_payload,
)
from app.adapters.llm.offline_llm_adapter import build_response
from app.schemas.constants.assistants import (
    AssistantToolName,
    AutotestScenarioKind,
    JudgeCriterion,
    LlmEffort,
)
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.conversations import LlmRequest, LlmToolDefinition, LlmToolResult
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.utilities.assembly.autotest_prompts import (
    DONE_MARKER,
    JUDGE_SYSTEM_PROMPT,
    build_customer_persona_prompt,
)
from app.utilities.assembly.autotest_scenarios import build_goal, build_scenario_key
from app.utilities.conversations.customer_text_fencing import fence_customer_text
from app.utilities.conversations.turn_context import CUSTOMER_HEADER
from app.utilities.llm_rehearsal.assistant_phrases import (
    ASSISTANT_PHRASES,
    RehearsalReply,
)
from app.utilities.llm_rehearsal.customer_phrases import (
    CUSTOMER_PHRASES,
    RehearsalIntent,
)
from app.utilities.llm_rehearsal.rehearsal_turns import play_rehearsal_turn

ASSISTANT_PROMPT = SystemPromptText("You are the assistant of a Georgian restaurant.")
ALL_TOOLS = (
    AssistantToolName.CHECK_AVAILABILITY,
    AssistantToolName.CREATE_BOOKING,
    AssistantToolName.HANDOFF_TO_HUMAN,
)


def ask(
    system_prompt: str, transcript: list[str], tools: tuple[AssistantToolName, ...] = ()
) -> ScriptedLlmTurn:
    return play_rehearsal_turn(
        LlmRequest(
            model_id=LlmModelId("scripted"),
            system_prompt=SystemPromptText(system_prompt),
            tools=[
                LlmToolDefinition(
                    name=name,
                    description=LlmToolDescription(name.value),
                    input_schema_json=LlmToolInputSchemaJson("{}"),
                )
                for name in tools
            ],
            transcript=[LlmProviderPayload(payload) for payload in transcript],
            max_output_tokens=LlmMaxOutputTokens(1000),
            effort=LlmEffort.LOW,
        )
    )


def customer_turn(text: str) -> str:
    """A platform user turn: the context, then the customer's fenced words."""

    return str(
        build_user_text_payload(
            MessageText(
                "Next days: Sun 2026-10-04, Mon 2026-10-05.\n"
                f"{CUSTOMER_HEADER}\n{fence_customer_text(text, 'k7')}"
            )
        )
    )


def answered(transcript: list[str], turn: ScriptedLlmTurn, result: object) -> list[str]:
    """The transcript after the assistant's tool call and the tool's result."""

    response = build_response(turn)
    return [
        *transcript,
        str(response.assistant_turn_payload),
        str(
            build_tool_results_payload(
                [
                    LlmToolResult(
                        call_id=LlmToolCallId(str(response.tool_calls[0].call_id)),
                        result_json=LlmToolResultJson(json.dumps(result)),
                    )
                ]
            )
        ),
    ]


def called(turn: ScriptedLlmTurn) -> tuple[str, dict[str, object]]:
    [call] = turn.tool_calls
    return call.tool_name.value, dict(json.loads(str(call.input_json)))


def test_the_judge_scores_every_criterion_five() -> None:
    turn = ask(JUDGE_SYSTEM_PROMPT, [customer_turn("Judge this")])

    verdict = json.loads(str(turn.text))
    assert verdict["notes"] == []
    assert verdict["scores"] == {criterion.value: 5 for criterion in JudgeCriterion}


def test_the_customer_says_its_goal_in_its_language_with_its_phone_then_stops() -> None:
    scenario = AutotestScenario(
        key=build_scenario_key(AutotestScenarioKind.BOOKING, LanguageTag("ka")),
        kind=AutotestScenarioKind.BOOKING,
        language=LanguageTag("ka"),
        language_name=LanguageDisplayName("Georgian"),
        goal=build_goal(AutotestScenarioKind.BOOKING, "table", 2),
    )
    persona = build_customer_persona_prompt(
        "Salobie Bia", scenario, E164PhoneNumber("+995555123456"), []
    )

    opening = ask(str(persona), [])
    after_reply = ask(
        str(persona),
        [
            str(
                build_response(
                    ScriptedLlmTurn(text=MessageText("Hi"))
                ).assistant_turn_payload
            )
        ],
    )

    assert str(opening.text).startswith(CUSTOMER_PHRASES["ka"][RehearsalIntent.BOOKING])
    assert "+995555123456" in str(opening.text)
    assert str(after_reply.text) == DONE_MARKER


def test_a_request_for_a_person_is_passed_on() -> None:
    transcript = [customer_turn("Hello, can I talk to a manager?")]

    handoff = ask(str(ASSISTANT_PROMPT), transcript, ALL_TOOLS)
    name, arguments = called(handoff)
    reply = ask(
        str(ASSISTANT_PROMPT),
        answered(
            transcript,
            handoff,
            {"customer_message": "A colleague will answer you soon."},
        ),
        ALL_TOOLS,
    )

    assert (name, arguments["reason"]) == ("handoff_to_human", "customer_request")
    assert str(reply.text) == "A colleague will answer you soon."


def test_a_booking_takes_the_first_free_time_of_the_next_days() -> None:
    words = f"{CUSTOMER_PHRASES['ru'][RehearsalIntent.BOOKING]} +995555123456"
    transcript = [customer_turn(words)]

    first_day = ask(str(ASSISTANT_PROMPT), transcript, ALL_TOOLS)
    transcript = answered(transcript, first_day, {"slots": []})
    next_day = ask(str(ASSISTANT_PROMPT), transcript, ALL_TOOLS)
    transcript = answered(
        transcript, next_day, {"slots": [{"date": "2026-10-05", "time": "19:00"}]}
    )
    booking = ask(str(ASSISTANT_PROMPT), transcript, ALL_TOOLS)
    transcript = answered(transcript, booking, {"booking_id": "booking_1"})
    confirmed = ask(str(ASSISTANT_PROMPT), transcript, ALL_TOOLS)

    assert called(first_day) == (
        "check_availability",
        {"date": "2026-10-04", "party_size": 1},
    )
    assert called(next_day)[1]["date"] == "2026-10-05"
    name, arguments = called(booking)
    assert name == "create_booking"
    assert (arguments["name"], arguments["phone"], arguments["time"]) == (
        "Анна",
        "+995555123456",
        "19:00",
    )
    assert str(confirmed.text) == ASSISTANT_PHRASES["ru"][RehearsalReply.BOOKED]


def test_with_no_free_time_left_the_assistant_says_so() -> None:
    words = CUSTOMER_PHRASES["en"][RehearsalIntent.BOOKING]
    transcript = [customer_turn(words)]
    for _ in range(2):
        transcript = answered(
            transcript, ask(str(ASSISTANT_PROMPT), transcript, ALL_TOOLS), {"slots": []}
        )

    reply = ask(str(ASSISTANT_PROMPT), transcript, ALL_TOOLS)

    assert str(reply.text) == ASSISTANT_PHRASES["en"][RehearsalReply.NO_TIME]


def test_other_questions_get_the_test_answer_in_the_customers_script() -> None:
    georgian = ask(
        str(ASSISTANT_PROMPT),
        [customer_turn("გამარჯობა, რა ღირს ხაჭაპური?")],
        ALL_TOOLS,
    )
    russian = ask(str(ASSISTANT_PROMPT), [customer_turn("Сколько стоит хачапури?")])

    assert str(georgian.text) == ASSISTANT_PHRASES["ka"][RehearsalReply.ANSWER]
    assert str(russian.text) == ASSISTANT_PHRASES["ru"][RehearsalReply.ANSWER]
