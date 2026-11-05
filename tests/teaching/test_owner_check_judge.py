"""
The semantic judge of the owner's checks that must (not) mention a phrase
(LLM_JUDGE_MODEL_ID): an answer that says it in other words passes
MUST_MENTION, one that says the forbidden thing in other words fails
MUST_NOT_MENTION, and its note is kept. The word rules decide alone when
the words already did, on the scripted model, without a key (a provider
error) and when the judge's answer cannot be read.
"""

import json

import pytest

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.assistants import AutotestCheckCode, AutotestExpectation
from app.schemas.dto.assistants.autotest_runs import (
    OwnerCheckDecision,
    OwnerCheckSpec,
)
from app.schemas.dto.conversations import AssistantReply, LlmResponse
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.autotests.owner_check_judge import OwnerCheckJudge
from app.utilities.assembly.owner_check_judging import parse_owner_check_verdict
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.brain.scripted_turns import say

QUESTION: str = "Можно прийти с собакой?"
JUDGE_COST: CostMicroUsd = CostMicroUsd(7)


def spec(expectation: AutotestExpectation, text: str | None) -> OwnerCheckSpec:
    return OwnerCheckSpec(
        case_id=AutotestCaseId(),
        question=AutotestCaseQuestion(QUESTION),
        expectation=expectation,
        expected_text=None if text is None else AutotestExpectedText(text),
    )


def reply(text: str) -> AssistantReply:
    return AssistantReply(
        conversation_id=ConversationId(),
        text=MessageText(text),
        language=LanguageTag("ru"),
        is_handed_off=False,
    )


def judge_with(
    judge: ScriptedLlmAdapter, judge_model: str = "claude-sonnet-5-5"
) -> OwnerCheckJudge:
    settings = assemble_app_settings(
        {"LLM_PROVIDER": "openai", "LLM_JUDGE_MODEL_ID": judge_model}
    )

    def cost(response: LlmResponse) -> CostMicroUsd:
        del response
        return JUDGE_COST

    return OwnerCheckJudge(judge, settings, cost)


def verdict(conveys: bool, note: str = "Собакам рады на веранде.") -> str:
    return json.dumps({"conveys": conveys, "note": note}, ensure_ascii=False)


def decide(
    judge: OwnerCheckJudge, check: OwnerCheckSpec, answer: str
) -> OwnerCheckDecision:
    return judge.decide(check, [reply(answer)], LanguageTag("ru"))


def test_other_words_with_the_same_meaning_pass_must_mention() -> None:
    model = ScriptedLlmAdapter.from_turns([say(verdict(True))])

    decision = decide(
        judge_with(model),
        spec(AutotestExpectation.MUST_MENTION, "с собакой можно"),
        "Да, питомцы у нас желанные гости.",
    )

    assert decision.failures == []
    assert [str(note) for note in decision.notes] == ["Собакам рады на веранде."]
    assert decision.cost == JUDGE_COST
    [request] = model.requests
    assert str(request.model_id) == "claude-sonnet-5-5"
    assert "с собакой можно" in str(request.transcript)


def test_a_judge_that_finds_no_such_meaning_keeps_the_failure() -> None:
    model = ScriptedLlmAdapter.from_turns([say(verdict(False, "Нет ответа."))])

    decision = decide(
        judge_with(model),
        spec(AutotestExpectation.MUST_MENTION, "с собакой можно"),
        "Я тестовый помощник.",
    )

    assert [failure.code for failure in decision.failures] == [
        AutotestCheckCode.EXPECTED_TEXT_MISSING
    ]
    assert [str(note) for note in decision.notes] == ["Нет ответа."]


def test_the_forbidden_meaning_in_other_words_fails_must_not_mention() -> None:
    model = ScriptedLlmAdapter.from_turns([say(verdict(True, "Обещана скидка."))])

    decision = decide(
        judge_with(model),
        spec(AutotestExpectation.MUST_NOT_MENTION, "скидка"),
        "Для вас сделаем дешевле на десять процентов.",
    )

    assert [failure.code for failure in decision.failures] == [
        AutotestCheckCode.FORBIDDEN_TEXT_MENTIONED
    ]
    assert decision.cost == JUDGE_COST


@pytest.mark.parametrize(
    ("expectation", "text", "answer"),
    [
        # The words already decide: the judge is not asked.
        (AutotestExpectation.MUST_MENTION, "с собакой можно", "Да, с собакой можно!"),
        (AutotestExpectation.MUST_NOT_MENTION, "скидка", "Скидка 10 %."),
        (AutotestExpectation.MUST_HAND_OFF, None, "Я тестовый помощник."),
    ],
)
def test_the_judge_is_not_asked_when_the_rules_decide(
    expectation: AutotestExpectation, text: str | None, answer: str
) -> None:
    model = ScriptedLlmAdapter.from_turns([])

    decision = decide(judge_with(model), spec(expectation, text), answer)

    assert model.requests == []
    assert decision.notes == [] and decision.cost == CostMicroUsd(0)


def test_the_scripted_rehearsal_model_leaves_it_to_the_rules() -> None:
    model = ScriptedLlmAdapter.from_turns([])

    decision = decide(
        judge_with(model, judge_model="scripted"),
        spec(AutotestExpectation.MUST_MENTION, "с собакой можно"),
        "Да, питомцы у нас желанные гости.",
    )

    assert model.requests == []
    assert [failure.code for failure in decision.failures] == [
        AutotestCheckCode.EXPECTED_TEXT_MISSING
    ]


def test_without_a_key_or_a_readable_answer_the_rules_decide() -> None:
    # No key: the provider refuses (the scripted model runs out of turns).
    failing = ScriptedLlmAdapter.from_turns([])
    unreadable = ScriptedLlmAdapter.from_turns([say("Да, наверное.")])
    check = spec(AutotestExpectation.MUST_MENTION, "с собакой можно")

    refused = decide(judge_with(failing), check, "Питомцы — желанные гости.")
    garbled = decide(judge_with(unreadable), check, "Питомцы — желанные гости.")

    assert [failure.code for failure in refused.failures] == [
        AutotestCheckCode.EXPECTED_TEXT_MISSING
    ]
    assert refused.cost == CostMicroUsd(0)
    assert [failure.code for failure in garbled.failures] == [
        AutotestCheckCode.EXPECTED_TEXT_MISSING
    ]
    # The unreadable answer was still paid for.
    assert garbled.cost == JUDGE_COST


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (None, None),
        ("not json", None),
        ('{"conveys": "yes"}', None),
        ('```json\n{"conveys": false}\n```', (False, None)),
        ('{"conveys": true, "note": "  Да.  "}', (True, "Да.")),
    ],
)
def test_the_verdict_is_read_strictly(
    answer: str | None, expected: tuple[bool, str | None] | None
) -> None:
    read = parse_owner_check_verdict(answer)

    assert (
        None if read is None else (read[0], None if read[1] is None else str(read[1]))
    ) == expected
