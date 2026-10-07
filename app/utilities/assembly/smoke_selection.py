"""
The quick check of "Apply changes" (concept section 11, daily edits).

A full autotest run crosses every language with every scenario kind and
takes minutes of model calls; an owner who changed a price waits for a
handful instead: the scenario kinds the changes touch and three core ones,
in the default language (the core ones in every language when the
languages changed), plus a price question for each offer item that
changed. The pass rules stay the same (every price and booking scenario
passes, an average judge score of at least 4); the whole suite stays
available from Advanced.
"""

from collections.abc import Collection, Mapping, Sequence

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.setup import PendingChangeAction, PendingChangeArea
from app.schemas.dto.assistants.autotest_runs import AutotestLanguage, AutotestScenario
from app.schemas.dto.assistants.smoke_checks import (
    SmokeCheckSelection,
    SmokeScenarioPick,
)
from app.schemas.dto.billing import Money
from app.schemas.dto.setup.pending_changes import PendingChange
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_scenarios import (
    RED_TEAM_SCENARIO_KINDS,
    build_goal,
    build_price_goal,
    build_scenario_key,
    expected_prices,
)

# In order of preference; the first three the version can play are the core.
CORE_SMOKE_KINDS: tuple[AutotestScenarioKind, ...] = (
    AutotestScenarioKind.BOOKING,
    AutotestScenarioKind.PRICE_QUESTION,
    AutotestScenarioKind.HUMAN_REQUEST,
    AutotestScenarioKind.PROMPT_INJECTION,
    AutotestScenarioKind.UNKNOWN_QUESTION,
    AutotestScenarioKind.RUDE_CUSTOMER,
)
CORE_SMOKE_SCENARIO_COUNT: int = 3
MAX_SMOKE_PRICE_QUESTIONS: int = 3
TOUCHED_KINDS: Mapping[PendingChangeArea, tuple[AutotestScenarioKind, ...]] = {
    PendingChangeArea.PROFILE: (),
    # The rude customer asks about the opening hours.
    PendingChangeArea.HOURS: (
        AutotestScenarioKind.BOOKING_OUT_OF_HOURS,
        AutotestScenarioKind.RUDE_CUSTOMER,
    ),
    PendingChangeArea.SPECIAL_DAYS: (AutotestScenarioKind.BOOKING_OUT_OF_HOURS,),
    PendingChangeArea.ANSWERS: (AutotestScenarioKind.UNKNOWN_QUESTION,),
    PendingChangeArea.OFFER: (AutotestScenarioKind.PRICE_QUESTION,),
    PendingChangeArea.QUESTIONS: (AutotestScenarioKind.UNKNOWN_QUESTION,),
    PendingChangeArea.RESOURCES: (
        AutotestScenarioKind.BOOKING,
        AutotestScenarioKind.CANCELLATION,
    ),
    PendingChangeArea.BOOKING_RULES: (
        AutotestScenarioKind.BOOKING,
        AutotestScenarioKind.BOOKING_OUT_OF_HOURS,
        AutotestScenarioKind.CANCELLATION,
    ),
    PendingChangeArea.LINKS: (AutotestScenarioKind.UNKNOWN_QUESTION,),
    PendingChangeArea.LANGUAGES: (),
    PendingChangeArea.CALLS: (),
    # A new instruction faces every attack again.
    PendingChangeArea.CONVERSATION: (
        AutotestScenarioKind.HUMAN_REQUEST,
        AutotestScenarioKind.DISCOUNT_REQUEST,
        AutotestScenarioKind.PROMPT_INJECTION,
        AutotestScenarioKind.EMERGENCY,
        *RED_TEAM_SCENARIO_KINDS,
    ),
}


def select_core_kinds(
    applicable_kinds: Sequence[AutotestScenarioKind],
) -> list[AutotestScenarioKind]:
    """The three core scenario kinds this version can play."""

    return [kind for kind in CORE_SMOKE_KINDS if kind in applicable_kinds][
        :CORE_SMOKE_SCENARIO_COUNT
    ]


def select_smoke_checks(
    changes: Sequence[PendingChange],
    applicable_kinds: Sequence[AutotestScenarioKind],
    languages: Sequence[LanguageTag],
    default_language: LanguageTag,
    priced_item_titles: Collection[str],
) -> SmokeCheckSelection:
    """
    The quick check of the changes (in the version's template order of
    kinds): what they touch and the core kinds in `default_language`, the
    core kinds in the other `languages` too when the languages changed, and
    a price question for each changed offer item that has a price.
    """

    core_kinds: list[AutotestScenarioKind] = select_core_kinds(applicable_kinds)
    touched_kinds: set[AutotestScenarioKind] = {
        kind for change in changes for kind in TOUCHED_KINDS[change.area]
    }
    picks: list[SmokeScenarioPick] = [
        SmokeScenarioPick(kind=kind, language=default_language)
        for kind in applicable_kinds
        if kind in touched_kinds or kind in core_kinds
    ]
    if any(change.area is PendingChangeArea.LANGUAGES for change in changes):
        picks.extend(
            SmokeScenarioPick(kind=kind, language=language)
            for language in languages
            if language != default_language
            for kind in core_kinds
        )

    return SmokeCheckSelection(
        picks=picks,
        price_item_titles=changed_priced_titles(changes, priced_item_titles),
        price_language=default_language,
    )


def changed_priced_titles(
    changes: Sequence[PendingChange],
    priced_item_titles: Collection[str],
) -> list[KnowledgeTitle]:
    titles: list[KnowledgeTitle] = []
    for change in changes:
        title: str = "" if change.subject is None else str(change.subject)
        if (
            change.area is PendingChangeArea.OFFER
            and change.action is not PendingChangeAction.REMOVED
            and title in priced_item_titles
            and title not in titles
        ):
            titles.append(KnowledgeTitle(title))

    return titles[:MAX_SMOKE_PRICE_QUESTIONS]


def plan_smoke_scenarios(
    selection: SmokeCheckSelection,
    languages: Sequence[AutotestLanguage],
    applicable_kinds: Collection[AutotestScenarioKind],
    resource_noun: str,
    party_size: int,
    item_prices: Mapping[str, Money] | None = None,
) -> list[AutotestScenario]:
    """
    The scenarios of a quick check, keyed as a full run keys them; a pick
    the version can no longer play (a kind or language it does not have)
    is left out, and so are the attacks, which the planner plays in their
    own language (`red_team_scenarios.py`).
    """

    by_tag: dict[str, AutotestLanguage] = {str(item.tag): item for item in languages}
    scenarios: list[AutotestScenario] = []
    for pick in selection.picks:
        language: AutotestLanguage | None = by_tag.get(str(pick.language))
        if (
            language is None
            or pick.kind not in applicable_kinds
            or pick.kind in RED_TEAM_SCENARIO_KINDS
        ):
            continue

        scenarios.append(
            AutotestScenario(
                key=build_scenario_key(pick.kind, language.tag),
                kind=pick.kind,
                language=language.tag,
                language_name=language.name,
                language_script=language.script,
                goal=build_goal(pick.kind, resource_noun, party_size),
            )
        )

    price_language: AutotestLanguage | None = by_tag.get(str(selection.price_language))
    if price_language is None or AutotestScenarioKind.PRICE_QUESTION not in (
        applicable_kinds
    ):
        return scenarios

    for ordinal, title in enumerate(selection.price_item_titles, start=1):
        scenarios.append(
            AutotestScenario(
                key=build_scenario_key(
                    AutotestScenarioKind.PRICE_QUESTION, price_language.tag, ordinal
                ),
                kind=AutotestScenarioKind.PRICE_QUESTION,
                language=price_language.tag,
                language_name=price_language.name,
                language_script=price_language.script,
                goal=build_price_goal(str(title)),
                expected_prices=expected_prices(item_prices, str(title)),
            )
        )

    return scenarios
