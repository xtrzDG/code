"""
The parts of an autotest plan beyond languages x kinds: the language
scenarios, the attacks, the owner's own checks, the prices price questions
must name, and how often each scenario is played (pass^k).
"""

from collections.abc import Sequence

from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.assistants.autotest_runs import AutotestLanguage, AutotestScenario
from app.schemas.dto.billing import Money
from app.schemas.typings.assistants.constrained_integers import AutotestSampleCount
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_scenarios import (
    DEFAULT_PARTY_SIZE,
    LAUNCH_CRITICAL_SCENARIO_KINDS,
    plan_scenarios,
)
from app.utilities.assembly.language_profiles import (
    build_autotest_languages,
    collect_language_profiles,
)
from app.utilities.assembly.language_scenarios import (
    choose_foreign_languages,
    choose_transliterated_languages,
)
from app.utilities.assembly.owner_check_scenarios import plan_owner_check_scenarios
from app.utilities.assembly.red_team_scenarios import (
    RED_TEAM_LANGUAGE,
    plan_red_team_scenarios,
)


class ScenarioPlanningParts:
    """Plans the scenario groups that have their own languages or inputs."""

    def __init__(
        self,
        autotest_case_repo: AutotestCaseRepoContract,
        language_registry: LanguageRegistryContract,
        critical_samples: AutotestSampleCount,
    ) -> None:
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._critical_samples: AutotestSampleCount = critical_samples

    def languages(self, tags: Sequence[LanguageTag]) -> list[AutotestLanguage]:
        """Scenario languages with their English names and scripts."""

        return build_autotest_languages(
            tags, collect_language_profiles(self._language_registry, tags)
        )

    def language_scenarios(
        self,
        kinds: Sequence[AutotestScenarioKind],
        version: AssistantVersionDocument,
        languages: Sequence[LanguageTag],
    ) -> list[AutotestScenario]:
        """
        A customer writing a language the version does not list, and one
        typing a selected language in Latin letters, when those kinds run.
        """

        planned: list[tuple[AutotestScenarioKind, list[LanguageTag]]] = [
            (
                AutotestScenarioKind.FOREIGN_LANGUAGE,
                choose_foreign_languages(version.languages),
            ),
            (
                AutotestScenarioKind.TRANSLITERATED,
                choose_transliterated_languages(languages),
            ),
        ]
        return [
            scenario
            for kind, kind_languages in planned
            if kind in kinds
            for scenario in plan_scenarios(
                languages=self.languages(kind_languages),
                kinds=[kind],
                priced_item_titles=[],
                price_question_limit=0,
                resource_noun="",
                party_size=DEFAULT_PARTY_SIZE,
            )
        ]

    def red_team_scenarios(
        self, kinds: Sequence[AutotestScenarioKind]
    ) -> list[AutotestScenario]:
        """The attacks among `kinds`, in English."""

        return plan_red_team_scenarios(kinds, self.languages([RED_TEAM_LANGUAGE])[0])

    def owner_checks(
        self,
        business: BusinessDocument,
        languages: Sequence[LanguageTag] | None,
    ) -> list[AutotestScenario]:
        """The owner's active checks, in `languages` when they are given."""

        cases = [
            case
            for case in self._autotest_case_repo.list_by_business(business.id)
            if languages is None or case.language in languages
        ]
        case_languages: list[LanguageTag] = list(
            dict.fromkeys(case.language for case in cases)
        )
        return plan_owner_check_scenarios(cases, self.languages(case_languages))

    def sampled(self, scenarios: Sequence[AutotestScenario]) -> list[AutotestScenario]:
        """Launch-critical scenarios played AUTOTEST_CRITICAL_SAMPLES times."""

        return [
            scenario.model_copy(update={"sample_count": self._critical_samples})
            if scenario.kind in LAUNCH_CRITICAL_SCENARIO_KINDS
            else scenario
            for scenario in scenarios
        ]


def collect_item_prices(
    business: BusinessDocument,
    items: Sequence[KnowledgeItemDocument],
) -> dict[str, Money]:
    """
    The price each priced item's question must name, by title. A room type
    with seasonal rates is left out: the assistant may rightly quote the
    season's rate instead of the base one.
    """

    return {
        str(item.title): Money(
            amount_minor=item.price_minor,
            currency_code=item.currency_code or business.currency_code,
        )
        for item in items
        if item.is_active and item.price_minor is not None and not item.seasonal_rates
    }
