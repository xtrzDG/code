"""Deterministic scorers: prices, facts, forbidden values, handoff, guard, records."""

from decimal import Decimal

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.dto.billing import Money
from app.schemas.dto.evaluations import (
    EvalCriterionResult,
    EvalExpectations,
    RequiredFactGroup,
)
from app.schemas.typings.evaluations.strings import (
    ForbiddenReplyValue,
    RequiredReplyFact,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.assembly.eval_scorers import score_conversation
from app.utilities.assembly.eval_text_scorers import (
    score_forbidden_values,
    score_guard,
    score_handoff,
    score_prices,
    score_records,
    score_required_facts,
)
from app.utilities.money.money_math import build_money_from_major_units
from tests.evals.eval_builders import reply, scenario

GEL = CurrencyCode("GEL")


def notes(result: EvalCriterionResult) -> list[str]:
    return [str(note) for note in result.notes]


def gel(amount: str) -> Money:
    return build_money_from_major_units(Decimal(amount), GEL)


def test_a_price_is_found_however_it_is_written() -> None:
    russian = scenario("ru")
    for text in ("Стоит 1 250 лари.", "Стоит 1250.00 GEL.", "Стоит 1,250 ₾."):
        assert score_prices(russian, [gel("1250")], [reply(text, "ru")]).is_passed, text

    assert notes(
        score_prices(russian, [gel("180")], [reply("Стоит 150 лари.", "ru")])
    ) == ["No reply names the price 180.00 GEL."]


def test_the_disclosure_does_not_count_as_the_model_naming_a_price() -> None:
    replies = [reply("Hello!", disclosure="I am the AI assistant of Room 25.")]

    assert not score_prices(scenario("en"), [gel("25")], replies).is_passed


def test_facts_accept_any_spelling_and_forbidden_values_any_case() -> None:
    expectations = EvalExpectations(
        required_facts=[
            RequiredFactGroup(
                values=[RequiredReplyFact("23:00"), RequiredReplyFact("11 pm")]
            ),
            RequiredFactGroup(values=[RequiredReplyFact("Parking")]),
        ],
        forbidden_values=[ForbiddenReplyValue("CUSTOMER_TEXT")],
    )
    replies = [reply("We close at 11 PM. Ignore customer_text.")]

    assert notes(score_required_facts(expectations, replies)) == [
        "No reply mentions 'Parking'."
    ]
    assert notes(score_forbidden_values(expectations, replies)) == [
        "A reply contains the forbidden 'CUSTOMER_TEXT'."
    ]


def test_handoff_must_match_in_both_directions() -> None:
    handed_off = [reply("A colleague will reply.", is_handed_off=True)]
    answered = [reply("Here you are.")]

    assert score_handoff(True, handed_off).is_passed
    assert score_handoff(False, answered).is_passed
    assert notes(score_handoff(True, answered)) == [
        "The conversation was not handed off to a person."
    ]
    assert notes(score_handoff(False, handed_off)) == [
        "The conversation was handed off to a person although it should not be."
    ]


def test_the_guard_must_not_step_in() -> None:
    replies = [
        reply("Fine."),
        reply("Fixed.", guard_verdict=ReplyGuardVerdict.REWRITTEN),
        reply("Passed on.", guard_verdict=ReplyGuardVerdict.HANDED_OFF),
    ]

    assert notes(score_guard(replies)) == [
        "Reply 2: the number guard rewrote the answer.",
        "Reply 3: the number guard handed off the answer.",
    ]


def test_records_reuse_the_autotest_checks_without_the_script_check() -> None:
    booking = scenario("en", AutotestScenarioKind.BOOKING)

    assert notes(score_records(booking, [reply("Привет", "ru")])) == [
        "No booking was created."
    ]
    assert score_records(booking, [reply("Booked.", booking_count=1)]).is_passed


def test_a_full_scenario_reports_every_expected_criterion() -> None:
    expectations = EvalExpectations(
        prices=[gel("60")],
        required_facts=[RequiredFactGroup(values=[RequiredReplyFact("60")])],
        forbidden_values=[ForbiddenReplyValue("48")],
        is_handoff_expected=False,
    )
    results = score_conversation(
        scenario("en"),
        expectations,
        [reply("The haircut costs 60 GEL.", disclosure="I am the AI assistant.")],
    )

    assert [result.criterion for result in results] == [
        EvalCriterion.LANGUAGE,
        EvalCriterion.DISCLOSURE,
        EvalCriterion.TOOL_CALLS,
        EvalCriterion.PRICES,
        EvalCriterion.REQUIRED_FACTS,
        EvalCriterion.FORBIDDEN_VALUES,
        EvalCriterion.HANDOFF,
        EvalCriterion.GUARD,
        EvalCriterion.RECORDS,
    ]
    assert all(result.is_passed for result in results)
