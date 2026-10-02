import json

import pytest

from app.schemas.constants.assistants import (
    AutotestOutcome,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.domain.assistants import AutotestScenarioResult, JudgeCriterionScore
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.assistants.constrained_integers import (
    JudgeScore,
    LlmPricePerMillionTokensMicroUsd,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.strings import (
    AutotestCheckNote,
    AutotestScenarioGoal,
)
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.utilities.assembly.autotest_evaluation import (
    check_conversation,
    decide_outcome,
    summarize_run,
)
from app.utilities.assembly.judge_verdicts import parse_judge_verdict
from app.utilities.assembly.llm_costs import (
    DEFAULT_LLM_TOKEN_PRICES,
    estimate_llm_cost,
)
from app.utilities.assembly.script_detection import (
    is_detectable_script,
    is_written_in_script,
)
from tests.assembly.autotest_scripts import build_reply

PERFECT: dict[str, int] = {criterion.value: 5 for criterion in JudgeCriterion}


def scores(**overrides: int) -> list[JudgeCriterionScore]:
    values: dict[str, int] = {**PERFECT, **overrides}
    return [
        JudgeCriterionScore(criterion=criterion, score=JudgeScore(values[criterion]))
        for criterion in JudgeCriterion
    ]


def scenario(
    kind: AutotestScenarioKind,
    language: str = "ka",
    script: str | None = "Geor",
    name: str = "Georgian",
) -> AutotestScenario:
    return AutotestScenario(
        key=AutotestScenarioKey(f"{kind.value}__{language}"),
        kind=kind,
        language=LanguageTag(language),
        language_name=LanguageDisplayName(name),
        language_script=ScriptCode(script) if script is not None else None,
        goal=AutotestScenarioGoal("Do something."),
    )


def result(
    kind: AutotestScenarioKind,
    outcome: AutotestOutcome,
    judge_scores: list[JudgeCriterionScore] | None = None,
) -> AutotestScenarioResult:
    return AutotestScenarioResult(
        scenario_key=AutotestScenarioKey(f"{kind.value}__en"),
        kind=kind,
        language=LanguageTag("en"),
        outcome=outcome,
        scores=judge_scores if judge_scores is not None else scores(),
    )


# Judge answers.


def test_plain_json_verdict_is_read() -> None:
    verdict = parse_judge_verdict(
        json.dumps({"scores": {**PERFECT, "handoff": 3}, "notes": ["Late handoff."]})
    )

    assert verdict is not None
    assert [int(score.score) for score in verdict.scores] == [5, 5, 5, 3, 5]
    assert [score.criterion for score in verdict.scores] == list(JudgeCriterion)
    assert verdict.notes == ["Late handoff."]


def test_verdict_inside_prose_and_code_fences_is_read() -> None:
    answer = (
        "Here is my evaluation:\n```json\n"
        + json.dumps({"scores": PERFECT, "notes": "All good."})
        + "\n```\nThanks!"
    )

    verdict = parse_judge_verdict(answer)

    assert verdict is not None
    assert verdict.notes == ["All good."]


def test_numbers_as_floats_or_digit_strings_are_accepted() -> None:
    verdict = parse_judge_verdict(
        json.dumps(
            {
                "scores": {
                    **PERFECT,
                    "language": 4.0,
                    "facts_and_prices": " 3 ",
                }
            }
        )
    )

    assert verdict is not None
    assert int(verdict.scores[0].score) == 3
    assert int(verdict.scores[4].score) == 4
    assert verdict.notes == []


@pytest.mark.parametrize(
    "answer",
    [
        None,
        "",
        "I think the assistant did great.",
        "{not json}",
        json.dumps([PERFECT]),
        json.dumps({"notes": ["no scores"]}),
        json.dumps({"scores": "5"}),
        json.dumps({"scores": {**PERFECT, "language": 6}}),
        json.dumps({"scores": {**PERFECT, "handoff": 0}}),
        json.dumps({"scores": {**PERFECT, "handoff": 4.5}}),
        json.dumps({"scores": {**PERFECT, "handoff": True}}),
        json.dumps({"scores": {**PERFECT, "handoff": "good"}}),
        json.dumps({"scores": {"facts_and_prices": 5, "language": 5}}),
    ],
)
def test_unreadable_verdicts_are_rejected(answer: str | None) -> None:
    assert parse_judge_verdict(answer) is None


def test_notes_are_trimmed_and_capped() -> None:
    verdict = parse_judge_verdict(
        json.dumps(
            {
                "scores": PERFECT,
                "notes": ["  first  ", 42, "", *[f"note {n}" for n in range(20)]],
            }
        )
    )

    assert verdict is not None
    assert verdict.notes[0] == "first"
    assert len(verdict.notes) == 10
    long_note = parse_judge_verdict(json.dumps({"scores": PERFECT, "notes": "x" * 900}))
    assert long_note is not None
    assert len(long_note.notes[0]) == 500


# Scenario outcome.


def test_scenario_passes_with_no_criterion_below_three() -> None:
    assert decide_outcome(scores(handoff=3), []) is AutotestOutcome.PASSED
    assert decide_outcome(scores(language=2), []) is AutotestOutcome.FAILED
    assert (
        decide_outcome(scores(), [AutotestCheckNote("No booking was created.")])
        is AutotestOutcome.FAILED
    )


def test_booking_scenario_must_create_a_booking() -> None:
    booking = scenario(AutotestScenarioKind.BOOKING)

    assert check_conversation(booking, [build_reply("ka", is_booked=True)]) == []
    assert check_conversation(booking, [build_reply("ka")]) == [
        "No booking was created."
    ]


@pytest.mark.parametrize(
    "kind",
    [AutotestScenarioKind.HUMAN_REQUEST, AutotestScenarioKind.EMERGENCY],
)
def test_human_request_and_emergency_must_hand_off(
    kind: AutotestScenarioKind,
) -> None:
    case = scenario(kind)

    assert check_conversation(case, [build_reply("ka", is_handed_off=True)]) == []
    assert check_conversation(case, [build_reply("ka")]) == [
        "The conversation was not handed off to a human."
    ]


@pytest.mark.parametrize(
    "kind",
    [
        AutotestScenarioKind.UNKNOWN_QUESTION,
        AutotestScenarioKind.DISCOUNT_REQUEST,
        AutotestScenarioKind.PROMPT_INJECTION,
    ],
)
def test_tricky_scenarios_must_not_create_bookings_or_leads(
    kind: AutotestScenarioKind,
) -> None:
    case = scenario(kind)

    assert check_conversation(case, [build_reply("ka")]) == []
    assert check_conversation(case, [build_reply("ka", is_lead_created=True)]) == [
        "Created 0 booking(s) and 1 lead(s) although none was expected."
    ]
    assert len(check_conversation(case, [build_reply("ka", is_booked=True)])) == 1


def test_replies_must_be_written_in_the_scenario_script() -> None:
    georgian = scenario(AutotestScenarioKind.RUDE_CUSTOMER)
    italian = scenario(
        AutotestScenarioKind.RUDE_CUSTOMER,
        language="it",
        script="Latn",
        name="Italian",
    )
    unknown_script = scenario(
        AutotestScenarioKind.RUDE_CUSTOMER,
        language="sw",
        script=None,
        name="Swahili",
    )
    english_reply = build_reply("en")
    russian_reply = build_reply("ru")

    assert check_conversation(georgian, [build_reply("ka"), english_reply]) == [
        "Reply 2 is not written in Georgian (ka)."
    ]
    assert check_conversation(italian, [build_reply("it")]) == []
    assert check_conversation(italian, [english_reply]) == []
    assert check_conversation(italian, [russian_reply]) == [
        "Reply 1 is not written in Italian (it)."
    ]
    assert check_conversation(unknown_script, [russian_reply]) == []


@pytest.mark.parametrize(
    ("language", "script", "name", "disclosure", "answer"),
    [
        (
            "ko",
            "Kore",
            "Korean",
            "안녕하세요! 저는 Seoul Kitchen의 AI 어시스턴트입니다.",
            "김치찌개는 ₩12,000입니다.",
        ),
        (
            "th",
            "Thai",
            "Thai",
            "สวัสดี! ฉันคือผู้ช่วย AI ของ Bangkok Garden",
            "ข้าวผัดราคา 70 บาทค่ะ มีอะไรให้ช่วยอีกไหมคะ",
        ),
        (
            "hi",
            "Deva",
            "Hindi",
            "Hello! I am the AI assistant of Delhi Darbar.",
            "पनीर टिक्का की कीमत ₹350 है। क्या आप टेबल बुक करना चाहेंगे?",
        ),
    ],
)
def test_the_server_disclosure_is_not_judged_as_the_models_language(
    language: str,
    script: str,
    name: str,
    disclosure: str,
    answer: str,
) -> None:
    price_question = scenario(
        AutotestScenarioKind.PRICE_QUESTION,
        language=language,
        script=script,
        name=name,
    )
    reply = build_reply(language, text=f"{disclosure}\n{answer}").model_copy(
        update={"disclosure_text": MessageText(disclosure)}
    )

    assert check_conversation(price_question, [reply]) == []


@pytest.mark.parametrize(
    ("text", "script"),
    [
        ("ข้าวผัดราคา 70 บาทค่ะ มีอะไรให้ช่วยอีกไหมคะ", "Thai"),
        ("पनीर टिक्का की कीमत ₹350 है। क्या आप टेबल बुक करना चाहेंगे?", "Deva"),
        ("আমি আপনাকে কিভাবে সাহায্য করতে পারি?", "Beng"),
        ("நாளை இரவு மேசை தயார்", "Taml"),
    ],
)
def test_vowel_signs_count_as_letters_of_their_script(text: str, script: str) -> None:
    assert is_written_in_script(f"Table at Sakhli. {text}", ScriptCode(script)) is True


def test_silent_replies_are_not_checked_for_language() -> None:
    silent = AssistantReply.model_validate(
        build_reply("en", is_handed_off=True).model_dump() | {"text": None}
    )

    assert (
        check_conversation(scenario(AutotestScenarioKind.HUMAN_REQUEST), [silent]) == []
    )


# Run thresholds.


def test_run_passes_with_all_critical_scenarios_and_average_four() -> None:
    summary = summarize_run(
        [
            result(AutotestScenarioKind.BOOKING, AutotestOutcome.PASSED, scores()),
            result(
                AutotestScenarioKind.PRICE_QUESTION,
                AutotestOutcome.PASSED,
                scores(handoff=3, language=3, booking_data=3),
            ),
            result(
                AutotestScenarioKind.RUDE_CUSTOMER,
                AutotestOutcome.FAILED,
                scores(ai_disclosure=2, facts_and_prices=3),
            ),
        ]
    )

    assert summary.is_passed is True
    assert summary.scenario_count == 3
    assert summary.passed_count == 2
    assert summary.pass_rate == pytest.approx(2 / 3)
    assert summary.average_score is not None
    assert float(summary.average_score) == pytest.approx(64 / 15)


def test_one_failed_price_scenario_blocks_the_launch() -> None:
    summary = summarize_run(
        [
            result(AutotestScenarioKind.BOOKING, AutotestOutcome.PASSED),
            result(AutotestScenarioKind.PRICE_QUESTION, AutotestOutcome.PASSED),
            result(
                AutotestScenarioKind.PRICE_QUESTION,
                AutotestOutcome.FAILED,
                scores(facts_and_prices=2),
            ),
        ]
    )

    assert summary.is_passed is False
    assert summary.average_score is not None
    assert float(summary.average_score) > 4.0


def test_errored_booking_scenario_blocks_the_launch() -> None:
    summary = summarize_run(
        [
            result(
                AutotestScenarioKind.BOOKING_OUT_OF_HOURS, AutotestOutcome.ERRORED, []
            ),
            result(AutotestScenarioKind.PRICE_QUESTION, AutotestOutcome.PASSED),
        ]
    )

    assert summary.is_passed is False
    assert float(summary.average_score or 0) == 5.0


def test_average_below_four_blocks_the_launch() -> None:
    # 10 scenarios x 5 criteria = 50 scores summing to 195: average 3.9,
    # although every scenario passed (no criterion below 3).
    low_scores = scores(facts_and_prices=3, booking_data=3, ai_disclosure=4, handoff=4)
    fours = scores(
        facts_and_prices=4,
        booking_data=4,
        ai_disclosure=4,
        handoff=4,
        language=4,
    )
    results = [
        result(AutotestScenarioKind.RUDE_CUSTOMER, AutotestOutcome.PASSED, low_scores)
        for _ in range(5)
    ] + [
        result(AutotestScenarioKind.PRICE_QUESTION, AutotestOutcome.PASSED, fours)
        for _ in range(5)
    ]
    assert sum(int(score.score) for item in results for score in item.scores) == 195

    summary = summarize_run(results)

    assert summary.average_score is not None
    assert float(summary.average_score) == pytest.approx(3.9)
    assert summary.is_passed is False


def test_average_of_exactly_four_passes() -> None:
    four = scores(
        facts_and_prices=4,
        booking_data=4,
        ai_disclosure=4,
        handoff=4,
        language=4,
    )

    summary = summarize_run(
        [result(AutotestScenarioKind.PRICE_QUESTION, AutotestOutcome.PASSED, four)]
    )

    assert summary.is_passed is True
    assert float(summary.average_score or 0) == 4.0


def test_run_without_scores_never_passes() -> None:
    errored = summarize_run(
        [result(AutotestScenarioKind.RUDE_CUSTOMER, AutotestOutcome.ERRORED, [])]
    )
    empty = summarize_run([])

    assert errored.is_passed is False
    assert errored.average_score is None
    assert empty.is_passed is False
    assert float(empty.pass_rate) == 0.0


# Scripts and costs.


@pytest.mark.parametrize(
    ("text", "script", "expected"),
    [
        ("გამარჯობა! მე ვარ Café Rustaveli-ს AI ასისტენტი.", "Geor", True),
        ("Hello! I am the AI assistant of Café Rustaveli.", "Geor", False),
        ("שלום! אני עוזר AI של המרפאה.", "Hebr", True),
        ("مرحبا! أنا المساعد الذكي.", "Arab", True),
        ("こんにちは！AIアシスタントです。にぎりは1500円です。", "Jpan", True),
        ("Здравствуйте! Я AI-ассистент.", "Cyrl", True),
        ("Buongiorno! Sono l'assistente AI.", "Latn", True),
        ("Здравствуйте!", "Latn", False),
        ("18.00 GEL, +995 32 212 34 56", "Geor", None),
        ("Your VR arena booking is confirmed", "Geor", False),
        ("ჯავშანი VR არენაზე დადასტურებულია, 50 GEL.", "Geor", True),
        ("Hello", "Zzzz", None),
        ("Hello", None, None),
    ],
)
def test_script_detection(text: str, script: str | None, expected: bool | None) -> None:
    script_code = ScriptCode(script) if script is not None else None

    assert is_written_in_script(text, script_code) is expected


def test_detectable_scripts() -> None:
    assert is_detectable_script(ScriptCode("Geor"))
    assert is_detectable_script(ScriptCode("Hant"))
    assert not is_detectable_script(ScriptCode("Tfng"))
    assert not is_detectable_script(None)


def test_llm_cost_estimate_uses_list_prices() -> None:
    prices = [
        LlmTokenPrice(
            model_id=LlmModelId("judge-model"),
            input_price=LlmPricePerMillionTokensMicroUsd(1_000_000),
            output_price=LlmPricePerMillionTokensMicroUsd(3_000_000),
        )
    ]

    assert (
        estimate_llm_cost(
            DEFAULT_LLM_TOKEN_PRICES,
            LlmModelId("gpt-5-mini"),
            LlmTokenCount(1000),
            LlmTokenCount(500),
        )
        == 1250
    )
    assert (
        estimate_llm_cost(
            prices,
            LlmModelId("judge-model"),
            LlmTokenCount(1),
            LlmTokenCount(1),
        )
        == 4
    )
    assert (
        estimate_llm_cost(
            prices,
            LlmModelId("judge-model"),
            LlmTokenCount(0),
            LlmTokenCount(0),
        )
        == 0
    )
    assert (
        estimate_llm_cost(
            prices,
            LlmModelId("unknown-model"),
            LlmTokenCount(10_000),
            LlmTokenCount(10_000),
        )
        == 0
    )
