"""Deterministic scorers: language, disclosure, tool calls and their fields."""

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.dto.evaluations import (
    EvalCriterionResult,
    EvalExpectations,
    ExpectedToolCall,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.evaluations.constrained_strings import ToolInputFieldName
from app.schemas.typings.evaluations.strings import ExpectedToolFieldValue
from app.utilities.assembly.eval_scorers import (
    score_call_fields,
    score_conversation,
    score_disclosure,
    score_language,
    score_tool_calls,
)
from tests.evals.eval_builders import reply, scenario, tool_call

BOOK = AssistantToolName.CREATE_BOOKING
DISCLOSURE_KA = "გამარჯობა! მე ვარ Studio Rose-ის AI-ასისტენტი."


def notes(result: EvalCriterionResult) -> list[str]:
    return [str(note) for note in result.notes]


def booking_expectation(**fields: list[str]) -> EvalExpectations:
    return EvalExpectations(
        tool_calls=[
            ExpectedToolCall(
                tool_name=BOOK,
                fields={
                    ToolInputFieldName(name): [
                        ExpectedToolFieldValue(v) for v in values
                    ]
                    for name, values in fields.items()
                },
            )
        ]
    )


def test_language_needs_a_written_reply_in_the_script_and_language() -> None:
    georgian = scenario("ka")

    assert score_language(georgian, [reply("კარგი, გელოდებით!", "ka")]).is_passed
    assert notes(score_language(georgian, [reply(None, "ka")])) == [
        "The assistant wrote no reply."
    ]
    failed = notes(score_language(georgian, [reply("See you soon!", "en")]))
    assert failed == [
        "Reply 1 is not written in Georgian (Geor).",
        "Reply 1 was answered as en, not ka.",
    ]


def test_the_disclosure_comes_once_first_and_in_the_language() -> None:
    georgian = scenario("ka")
    good = [reply("რით დაგეხმაროთ?", "ka", DISCLOSURE_KA), reply("კარგი.", "ka")]

    assert score_disclosure(georgian, good).is_passed
    assert notes(score_disclosure(georgian, [reply("კარგი.", "ka")])) == [
        "The disclosure was given 0 times, not once."
    ]
    late = [reply("კარგი.", "ka"), reply("რით დაგეხმაროთ?", "ka", DISCLOSURE_KA)]
    assert notes(score_disclosure(georgian, late)) == [
        "The disclosure is not in the first reply."
    ]
    repeated = [
        reply("რით დაგეხმაროთ?", "ka", DISCLOSURE_KA),
        reply(DISCLOSURE_KA, "ka"),
    ]
    assert notes(score_disclosure(georgian, repeated)) == [
        "The disclosure text appears 2 times in the replies."
    ]


def test_a_latin_business_name_keeps_a_hebrew_disclosure_hebrew() -> None:
    hebrew = scenario("he")
    disclosure = "שלום! אני עוזר ה-AI של Rustaveli Terrace Hotel."
    replies = [reply("איך אפשר לעזור?", "he", disclosure)]

    assert not score_disclosure(hebrew, replies).is_passed
    assert score_disclosure(
        hebrew, replies, BusinessName("Rustaveli Terrace Hotel")
    ).is_passed


def test_expected_tools_must_be_called_and_forbidden_ones_must_not() -> None:
    expectations = EvalExpectations(
        tool_calls=[ExpectedToolCall(tool_name=AssistantToolName.HANDOFF_TO_HUMAN)],
        forbidden_tools=[BOOK],
    )
    called = [reply("Done.", tool_calls=[tool_call(BOOK, {"name": "Emma"})])]

    assert notes(score_tool_calls(expectations, called)) == [
        "handoff_to_human was not called.",
        "create_booking was called although the scenario forbids it.",
    ]


def test_booking_fields_must_match_the_persona() -> None:
    expectations = booking_expectation(
        name=["ნინო", "Nino"], phone=["+995555100201"], party_size=["2"]
    )
    matching = tool_call(
        BOOK, {"name": "Nino Beridze", "phone": "555 10 02 01", "party_size": 2}
    )
    wrong = tool_call(BOOK, {"name": "Nino", "phone": "+995555100201", "party_size": 3})
    failed_call = tool_call(
        BOOK, {"name": "Nino", "phone": "+995555100201", "party_size": 2}, is_error=True
    )

    assert score_call_fields(
        expectations, [reply("Ok", tool_calls=[matching])]
    ).is_passed
    assert notes(
        score_call_fields(expectations, [reply("Ok", tool_calls=[wrong])])
    ) == ["create_booking: party_size: wanted '2', got 3."]
    assert notes(
        score_call_fields(expectations, [reply("Ok", tool_calls=[failed_call])])
    ) == ["create_booking: create_booking was not called successfully."]


def test_the_whole_conversation_lists_only_criteria_that_apply() -> None:
    price_question = scenario("en", AutotestScenarioKind.PRICE_QUESTION)
    criteria = [
        result.criterion
        for result in score_conversation(
            price_question, EvalExpectations(), [reply("It costs 25 GEL.")]
        )
    ]

    assert criteria == [
        EvalCriterion.LANGUAGE,
        EvalCriterion.DISCLOSURE,
        EvalCriterion.TOOL_CALLS,
        EvalCriterion.GUARD,
        EvalCriterion.RECORDS,
    ]
