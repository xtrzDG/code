"""
The rehearsal model (LLM_PROVIDER=scripted) answers a question its fact
table answers, and its AI customer ends an owner check that goes on after
its question, so corrected answers and their checks pass offline.
"""

from app.adapters.llm.llm_payloads import build_user_text_payload
from app.schemas.constants.assistants import (
    AssistantToolName,
    AutotestExpectation,
    AutotestScenarioKind,
)
from app.schemas.dto.assistants.autotest_runs import AutotestScenario, OwnerCheckSpec
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.assistants.constrained_strings import AutotestCaseQuestion
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.assistants.strings import AutotestScenarioGoal
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.utilities.assembly.autotest_prompts import (
    DONE_MARKER,
    build_customer_persona_prompt,
    build_owner_check_continuation,
)
from app.utilities.assembly.owner_check_scenarios import owner_check_key
from app.utilities.llm_rehearsal.rehearsal_facts import find_fact_answer
from tests.pending_changes.test_rehearsal_model import ALL_TOOLS, ask, customer_turn

FACTS: str = "\n".join(
    [
        "Facts:",
        "- Opening hours on Monday: 12:00–23:00",
        "- Question: Можно прийти со своим тортом?: Да, подадим его бесплатно.",
        "- Policy: Dogs: Only on the terrace: on a leash.",
        "- Question: Empty answer?: ",
    ]
)


def test_a_question_of_the_fact_table_gets_its_answer() -> None:
    assert (
        find_fact_answer(FACTS, "можно прийти со СВОИМ тортом")
        == "Да, подадим его бесплатно."
    )
    assert find_fact_answer(FACTS, "Dogs") == "Only on the terrace: on a leash."
    assert find_fact_answer(FACTS, "Dogs: Only on the terrace") == "on a leash."


def test_other_questions_and_empty_rows_get_none() -> None:
    assert find_fact_answer(FACTS, "Opening hours on Monday") is None
    assert find_fact_answer(FACTS, "Есть парковка?") is None
    assert find_fact_answer(FACTS, "Empty answer") is None
    assert find_fact_answer(FACTS, "?!") is None


def test_the_rehearsal_assistant_answers_from_the_fact_table() -> None:
    turn = ask(FACTS, [customer_turn("Можно прийти со своим тортом?")], tools=ALL_TOOLS)

    assert turn.tool_calls == []
    assert str(turn.text) == "Да, подадим его бесплатно."


def test_the_rehearsal_customer_ends_an_owner_check_after_its_question() -> None:
    case_id = AutotestCaseId()
    scenario = AutotestScenario(
        key=owner_check_key(case_id),
        kind=AutotestScenarioKind.OWNER_CHECK,
        language=LanguageTag("ru"),
        language_name=LanguageDisplayName("Russian"),
        goal=AutotestScenarioGoal('Ask exactly: "Хочу банкет".'),
        owner_check=OwnerCheckSpec(
            case_id=case_id,
            question=AutotestCaseQuestion("Хочу банкет"),
            expectation=AutotestExpectation.MUST_CREATE_LEAD,
        ),
    )
    persona = build_customer_persona_prompt(
        "Salobie", scenario, E164PhoneNumber("+995555123456"), []
    )
    continuation = build_owner_check_continuation(
        "Хочу банкет",
        AssistantReply(
            conversation_id=ConversationId(),
            text=MessageText("Записал вашу заявку."),
            language=LanguageTag("ru"),
            is_handed_off=False,
        ),
    )

    turn = ask(str(persona), [str(build_user_text_payload(continuation))])

    assert str(turn.text) == DONE_MARKER
    assert AssistantToolName.CREATE_LEAD not in {
        call.tool_name for call in turn.tool_calls
    }
