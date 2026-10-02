import pytest

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.dto.assistants.autotest_runs import AutotestLanguage
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.utilities.assembly.assistant_tools import select_assistant_tools
from app.utilities.assembly.autotest_scenarios import (
    build_goal,
    build_scenario_key,
    list_applicable_kinds,
    plan_scenarios,
    select_kinds,
    select_languages,
)
from tests.assembly.fakes import ALL_BASE_KINDS

GEORGIAN = AutotestLanguage(
    tag=LanguageTag("ka"),
    name=LanguageDisplayName("Georgian"),
    script=ScriptCode("Geor"),
)
RUSSIAN = AutotestLanguage(
    tag=LanguageTag("ru"),
    name=LanguageDisplayName("Russian"),
    script=ScriptCode("Cyrl"),
)
ENGLISH = AutotestLanguage(
    tag=LanguageTag("en"),
    name=LanguageDisplayName("English"),
    script=ScriptCode("Latn"),
)
BOOKING_TOOLS = select_assistant_tools(takes_bookings=True, has_links=True)
LEAD_TOOLS = select_assistant_tools(takes_bookings=False, has_links=True)


def test_languages_times_kinds_plus_price_questions_in_turn() -> None:
    scenarios = plan_scenarios(
        languages=[GEORGIAN, RUSSIAN, ENGLISH],
        kinds=[AutotestScenarioKind.BOOKING, AutotestScenarioKind.PRICE_QUESTION],
        priced_item_titles=["Khachapuri", "Mtsvadi", "Lobio", "Pkhali"],
        price_question_limit=10,
        resource_noun="table",
        party_size=2,
    )

    assert [str(scenario.key) for scenario in scenarios] == [
        "booking__ka",
        "price_question__ka",
        "booking__ru",
        "price_question__ru",
        "booking__en",
        "price_question__en",
        "price_question__ka__1",
        "price_question__ru__2",
        "price_question__en__3",
        "price_question__ka__4",
    ]
    assert scenarios[6].goal == 'Ask how much "Khachapuri" costs.'
    assert scenarios[9].goal == 'Ask how much "Pkhali" costs.'
    assert scenarios[7].language_script == "Cyrl"
    assert scenarios[8].language_name == "English"


def test_price_questions_are_capped() -> None:
    titles = [f"Dish {number}" for number in range(25)]

    capped = plan_scenarios(
        languages=[ENGLISH],
        kinds=[AutotestScenarioKind.PRICE_QUESTION],
        priced_item_titles=titles,
        price_question_limit=10,
        resource_noun="table",
        party_size=2,
    )
    none = plan_scenarios(
        languages=[ENGLISH],
        kinds=[AutotestScenarioKind.PRICE_QUESTION],
        priced_item_titles=titles,
        price_question_limit=0,
        resource_noun="table",
        party_size=2,
    )

    assert len(capped) == 11
    assert str(capped[-1].key) == "price_question__en__10"
    assert len(none) == 1


def test_no_item_price_questions_without_the_price_kind() -> None:
    scenarios = plan_scenarios(
        languages=[ENGLISH],
        kinds=[AutotestScenarioKind.HUMAN_REQUEST],
        priced_item_titles=["Khachapuri"],
        price_question_limit=10,
        resource_noun="table",
        party_size=2,
    )

    assert [str(scenario.key) for scenario in scenarios] == ["human_request__en"]


def test_booking_kinds_apply_only_to_versions_that_book() -> None:
    with_bookings = list_applicable_kinds(
        [*ALL_BASE_KINDS, AutotestScenarioKind.BOOKING],
        BOOKING_TOOLS,
    )
    without_bookings = list_applicable_kinds(ALL_BASE_KINDS, LEAD_TOOLS)

    assert with_bookings == ALL_BASE_KINDS
    assert AutotestScenarioKind.BOOKING not in without_bookings
    assert AutotestScenarioKind.BOOKING_OUT_OF_HOURS not in without_bookings
    assert AutotestScenarioKind.CANCELLATION not in without_bookings
    assert AutotestScenarioKind.PRICE_QUESTION in without_bookings


def test_language_selection_keeps_version_order_and_rejects_others() -> None:
    available = [LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en")]

    assert select_languages(available, None) == available
    assert select_languages(available, [LanguageTag("en"), LanguageTag("ka")]) == [
        LanguageTag("ka"),
        LanguageTag("en"),
    ]
    with pytest.raises(ValidationFailedError, match="de"):
        select_languages(available, [LanguageTag("de")])

    with pytest.raises(ValidationFailedError, match="at least one"):
        select_languages(available, [])


def test_kind_selection_rejects_kinds_that_do_not_apply() -> None:
    applicable = list_applicable_kinds(ALL_BASE_KINDS, LEAD_TOOLS)

    assert select_kinds(applicable, None) == applicable
    assert select_kinds(
        applicable,
        [AutotestScenarioKind.HUMAN_REQUEST, AutotestScenarioKind.PRICE_QUESTION],
    ) == [AutotestScenarioKind.PRICE_QUESTION, AutotestScenarioKind.HUMAN_REQUEST]
    with pytest.raises(ValidationFailedError, match="booking"):
        select_kinds(applicable, [AutotestScenarioKind.BOOKING])

    with pytest.raises(ValidationFailedError, match="at least one"):
        select_kinds(applicable, [])


def test_scenario_keys_are_lower_case_and_valid() -> None:
    assert build_scenario_key(AutotestScenarioKind.BOOKING, LanguageTag("ka")) == (
        "booking__ka"
    )
    assert (
        build_scenario_key(
            AutotestScenarioKind.PRICE_QUESTION,
            LanguageTag("pt-BR"),
            3,
        )
        == "price_question__pt-br__3"
    )
    assert (
        build_scenario_key(AutotestScenarioKind.EMERGENCY, LanguageTag("zh-Hant"))
        == "emergency__zh-hant"
    )


def test_goals_describe_what_the_customer_tries() -> None:
    booking = build_goal(AutotestScenarioKind.BOOKING, "table", 2)
    solo = build_goal(AutotestScenarioKind.BOOKING_OUT_OF_HOURS, "doctor's visit", 1)

    assert booking.startswith("Book a table for 2 people")
    assert "give your name and phone number" in booking
    assert solo.startswith("Ask to book a doctor's visit for 1 person")
    assert "closed" in solo
    assert "human" in build_goal(AutotestScenarioKind.HUMAN_REQUEST, "table", 2)
    assert "Forget your instructions" in build_goal(
        AutotestScenarioKind.PROMPT_INJECTION,
        "table",
        2,
    )
    assert "emergency" in build_goal(AutotestScenarioKind.EMERGENCY, "table", 2)
    assert "discount" in build_goal(AutotestScenarioKind.DISCOUNT_REQUEST, "x", 2)
    for kind in AutotestScenarioKind:
        assert build_goal(kind, "table", 2).strip() != ""


def test_tools_without_create_booking_drop_booking_scenarios() -> None:
    kinds = list_applicable_kinds(
        ALL_BASE_KINDS,
        [AssistantToolName.CHECK_AVAILABILITY, AssistantToolName.GET_PRICE],
    )

    assert AutotestScenarioKind.BOOKING not in kinds
