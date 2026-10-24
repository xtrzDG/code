"""
A niche's own booking autotests (`BookingScenarioVariant`), planned from
the business's services and rooms: "a 45-minute haircut with Nino", "the
deluxe room for 3 nights". They are booking scenarios (kind BOOKING, so a
booking must come out of them), keyed "booking__<language>__<n>" from 2
and asked in the business languages in turn. A variant the business has
nothing for (no service with a performer, no room type with rooms) is
left out.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import BookingScenarioVariant
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.assistants.autotest_runs import AutotestLanguage, AutotestScenario
from app.schemas.typings.assistants.strings import AutotestScenarioGoal
from app.utilities.assembly.autotest_scenarios import build_scenario_key
from app.utilities.bookings.bookable_offers import bookable_offers, performers_of

STAY_NIGHTS: int = 3
FIRST_VARIANT_ORDINAL: int = 2
CONFIRMATION: str = (
    "When asked, give your name and phone number, and confirm the details "
    "the assistant repeats back to you."
)


def performer_goal(service_title: str, performer_name: str) -> AutotestScenarioGoal:
    return AutotestScenarioGoal(
        f'Book "{service_title}" for yourself with {performer_name} (ask for '
        f"{performer_name} by name) on a day and at a time when the business is "
        f"open (see its opening hours). {CONFIRMATION}"
    )


def room_stay_goal(room_type_title: str, nights: int) -> AutotestScenarioGoal:
    return AutotestScenarioGoal(
        f'Book "{room_type_title}" for {nights} nights for two adults, checking '
        "in about a month from today. Ask what the whole stay costs before you "
        f"confirm. {CONFIRMATION}"
    )


def plan_variant_goals(
    variants: Sequence[BookingScenarioVariant],
    items: Sequence[KnowledgeItemDocument],
    resources: Sequence[ResourceDocument],
) -> list[AutotestScenarioGoal]:
    """The goal of each variant the business's offers allow, in variant order."""

    goals: list[AutotestScenarioGoal] = []
    for variant in variants:
        wanted: KnowledgeItemKind = (
            KnowledgeItemKind.ROOM_TYPE
            if variant is BookingScenarioVariant.ROOM_TYPE_STAY
            else KnowledgeItemKind.SERVICE
        )
        for offer in bookable_offers(items):
            if offer.kind is not wanted:
                continue

            performers: list[ResourceDocument] = performers_of(offer, resources, items)
            if not performers:
                continue

            goals.append(
                room_stay_goal(str(offer.title), STAY_NIGHTS)
                if variant is BookingScenarioVariant.ROOM_TYPE_STAY
                else performer_goal(str(offer.title), str(performers[0].name))
            )
            break

    return goals


def plan_variant_scenarios(
    languages: Sequence[AutotestLanguage],
    goals: Sequence[AutotestScenarioGoal],
) -> list[AutotestScenario]:
    """Goal i in language i modulo the number of languages, as a booking."""

    if not languages:
        return []

    scenarios: list[AutotestScenario] = []
    for index, goal in enumerate(goals):
        language: AutotestLanguage = languages[index % len(languages)]
        scenarios.append(
            AutotestScenario(
                key=build_scenario_key(
                    AutotestScenarioKind.BOOKING,
                    language.tag,
                    index + FIRST_VARIANT_ORDINAL,
                ),
                kind=AutotestScenarioKind.BOOKING,
                language=language.tag,
                language_name=language.name,
                language_script=language.script,
                goal=goal,
            )
        )

    return scenarios
