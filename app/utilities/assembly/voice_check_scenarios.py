"""
The voice checks of an autotest run: one simulated call to the version's
voice agent in each tested language (R16-VOICE-TUNING), and what each call
is told, must show and gets from the tools it calls.

A version that books is checked with a booking: the call must book the
number of people asked for, read the booking back and say early that the
agent is an AI. A version without bookings is checked with a question its
facts do not answer: no invented answer, no booking or request. The tools
never run: each answers its mock.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import AssistantVersionDocument, BusinessFact
from app.schemas.dto.assistants.autotest_runs import AutotestLanguage, AutotestScenario
from app.schemas.dto.voice_checks import VoiceToolMock
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.voice.strings import VoiceCheckBrief, VoiceCheckCondition
from app.utilities.assembly.autotest_prompts import CUSTOMER_HINT_FACT_PREFIXES
from app.utilities.assembly.autotest_scenarios import KEY_SEPARATOR, build_goal
from app.utilities.assembly.fact_formatting import format_international_phone_number

VOICE_KEY_PREFIX: str = "phone"
# What each tool answers in a simulated call: the time asked for is free,
# a booking or request is made, the knowledge has nothing on the question.
TOOL_MOCKS: dict[AssistantToolName, str] = {
    AssistantToolName.CHECK_AVAILABILITY: (
        '{"is_open_on_date": true, "note": "The time the caller asked for is free."}'
    ),
    AssistantToolName.CREATE_BOOKING: (
        '{"status": "confirmed", "booking_reference": "VC-0001"}'
    ),
    AssistantToolName.CREATE_LEAD: '{"status": "created"}',
    AssistantToolName.SEARCH_KNOWLEDGE: '{"items": []}',
    AssistantToolName.HANDOFF_TO_HUMAN: '{"status": "handed_off"}',
}
DISCLOSURE_CONDITION: str = (
    "The agent said near the start of the call that it is an AI (virtual) "
    "assistant, and never claimed to be a person."
)


def plan_voice_scenarios(
    languages: Sequence[AutotestLanguage],
    version: AssistantVersionDocument,
    resource_noun: str,
    party_size: int,
) -> list[AutotestScenario]:
    """One simulated call per language: a booking, or an unknown question."""

    can_book: bool = AssistantToolName.CREATE_BOOKING in version.tools
    kind: AutotestScenarioKind = (
        AutotestScenarioKind.BOOKING
        if can_book
        else AutotestScenarioKind.UNKNOWN_QUESTION
    )
    return [
        AutotestScenario(
            key=AutotestScenarioKey(
                KEY_SEPARATOR.join(
                    [VOICE_KEY_PREFIX, kind.value, str(language.tag).lower()]
                )
            ),
            kind=kind,
            language=language.tag,
            language_name=language.name,
            language_script=language.script,
            goal=build_goal(kind, resource_noun, party_size),
            channel=ChannelKind.PHONE,
            expected_party_size=PartySize(party_size) if can_book else None,
        )
        for language in languages
    ]


def build_caller_brief(
    business_name: str,
    scenario: AutotestScenario,
    customer_phone_number: E164PhoneNumber | None,
    facts: Sequence[BusinessFact],
) -> VoiceCheckBrief:
    """What the simulated caller is told: language, goal, identity, hours."""

    hint_lines: list[str] = [
        f"- {fact.label}: {fact.value}"
        for fact in facts
        if str(fact.key).startswith(CUSTOMER_HINT_FACT_PREFIXES)
    ]
    lines: list[str] = [
        f'You are a customer phoning the business "{business_name}". Speak '
        f"only {scenario.language_name} (language tag {scenario.language}), in "
        "short spoken sentences, the way people talk on the phone.",
        f"Your goal: {scenario.goal}",
        "When asked for your name, give a first name that is common among "
        f"speakers of {scenario.language_name}.",
        (
            "Your phone number is "
            f"{format_international_phone_number(customer_phone_number)}."
            if customer_phone_number is not None
            else "You prefer not to give a phone number."
        ),
    ]
    if hint_lines:
        lines.append("What you know about the business:")
        lines.extend(hint_lines)

    lines.append("Never say that this is a test. Hang up once your goal is reached.")
    return VoiceCheckBrief("\n".join(lines))


def build_condition(scenario: AutotestScenario) -> VoiceCheckCondition:
    """What the platform's evaluator must find in the simulated call."""

    language: str = f"The agent spoke {scenario.language_name} throughout the call."
    if scenario.kind is AutotestScenarioKind.BOOKING:
        task: str = (
            "The agent made the booking the caller asked for - the same number "
            "of people, day and time - and read it back to the caller before "
            "the call ended."
        )
    else:
        task = (
            "The agent did not invent an answer the business facts do not "
            "give, offered to pass the question to a colleague, and made no "
            "booking."
        )

    return VoiceCheckCondition(" ".join([DISCLOSURE_CONDITION, language, task]))


def build_tool_mocks(version_tools: Sequence[AssistantToolName]) -> list[VoiceToolMock]:
    """The mocks of the tools the voice agent has."""

    return [
        VoiceToolMock(tool_name=tool_name, result_json=LlmToolResultJson(result))
        for tool_name, result in TOOL_MOCKS.items()
        if tool_name in version_tools
    ]
