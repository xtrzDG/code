"""Which simulated calls an autotest run plans, and what each one is told."""

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import BusinessFact
from app.schemas.dto.assistants.autotest_runs import (
    AutotestLanguage,
    AutotestPlanningRequest,
    AutotestScenario,
)
from app.schemas.dto.assistants.smoke_checks import (
    SmokeCheckSelection,
    SmokeScenarioPick,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue
from app.utilities.assembly.voice_check_scenarios import (
    build_caller_brief,
    build_condition,
    build_tool_mocks,
    plan_voice_scenarios,
)
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.testbed import AssemblyTestbed

GEORGIAN = AutotestLanguage(
    tag=LanguageTag("ka"),
    name=LanguageDisplayName("Georgian"),
    script=ScriptCode("Geor"),
)


def voice_scenarios(scenarios: list[AutotestScenario]) -> list[AutotestScenario]:
    return [scenario for scenario in scenarios if scenario.channel is ChannelKind.PHONE]


def test_a_version_without_bookings_is_called_with_an_unknown_question() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = testbed.version(business.id, testbed.assemble(business.id).id)
    version.tools = [AssistantToolName.SEARCH_KNOWLEDGE]

    [planned] = plan_voice_scenarios([GEORGIAN], version, "table", 2)

    assert str(planned.key) == "phone__unknown_question__ka"
    assert planned.kind is AutotestScenarioKind.UNKNOWN_QUESTION
    assert planned.expected_party_size is None
    assert "made no booking" in str(build_condition(planned))
    assert [mock.tool_name for mock in build_tool_mocks(version.tools)] == [
        AssistantToolName.SEARCH_KNOWLEDGE
    ]


def test_the_caller_is_told_the_language_its_number_and_the_hours() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = testbed.version(business.id, testbed.assemble(business.id).id)
    [planned] = plan_voice_scenarios([GEORGIAN], version, "table", 2)

    brief = str(
        build_caller_brief(
            "Café Rustaveli",
            planned,
            E164PhoneNumber("+995599123456"),
            [
                BusinessFact(
                    key=FactKey("hours_monday"),
                    label=FactLabel("Monday"),
                    value=FactValue("12:00-23:00"),
                ),
                BusinessFact(
                    key=FactKey("menu_1"), label=FactLabel("Menu"), value=FactValue("x")
                ),
            ],
        )
    )

    assert "Speak only Georgian (language tag ka)" in brief
    assert "+995 599 12 34 56" in brief or "+995599123456" in brief
    assert "- Monday: 12:00-23:00" in brief
    assert "Menu" not in brief
    assert "Book a table for 2 people" in brief


def test_the_quick_check_calls_in_the_default_language_only() -> None:
    testbed = AssemblyTestbed()
    testbed.voice_checks.missing_settings = []
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = testbed.version(business.id, testbed.assemble(business.id).id)
    planned = testbed.plan_scenarios_use_case.run(
        AutotestPlanningRequest(
            business=business,
            version=version,
            smoke_check=SmokeCheckSelection(
                picks=[
                    SmokeScenarioPick(
                        kind=AutotestScenarioKind.BOOKING, language=LanguageTag("ru")
                    )
                ],
                price_language=LanguageTag("ka"),
            ),
        )
    )

    assert [str(item.key) for item in voice_scenarios(planned.scenarios)] == [
        "phone__booking__ka"
    ]


def test_a_narrowed_run_without_bookings_plays_no_call() -> None:
    testbed = AssemblyTestbed()
    testbed.voice_checks.missing_settings = []
    business = seed_georgian_restaurant(testbed, PlanKey.VOICE_AND_CHAT)
    version = testbed.version(business.id, testbed.assemble(business.id).id)
    planner = testbed.plan_scenarios_use_case

    narrowed = planner.run(
        AutotestPlanningRequest(
            business=business,
            version=version,
            languages=[LanguageTag("ru")],
            kinds=[AutotestScenarioKind.PRICE_QUESTION],
        )
    )
    booked = planner.run(
        AutotestPlanningRequest(
            business=business,
            version=version,
            languages=[LanguageTag("ru")],
            kinds=[AutotestScenarioKind.BOOKING],
        )
    )

    assert voice_scenarios(narrowed.scenarios) == []
    assert [str(item.key) for item in voice_scenarios(booked.scenarios)] == [
        "phone__booking__ru"
    ]
