from app.contracts.registries import (
    LanguageRegistryContract,
    NicheTemplateRegistryContract,
)
from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessProfileRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.assistants.autotest_runs import (
    AutotestLanguage,
    AutotestPlanningRequest,
    AutotestScenario,
    AutotestScenarioPlanning,
)
from app.schemas.dto.assistants.smoke_checks import SmokeCheckSelection
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.assistants.constrained_integers import (
    PriceQuestionScenarioLimit,
)
from app.schemas.typings.assistants.strings import AutotestScenarioGoal
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_scenarios import (
    DEFAULT_PARTY_SIZE,
    list_applicable_kinds,
    plan_scenarios,
    select_kinds,
    select_languages,
)
from app.utilities.assembly.booking_variant_scenarios import (
    plan_variant_goals,
    plan_variant_scenarios,
)
from app.utilities.assembly.fact_descriptions import RESOURCE_KIND_NOUNS
from app.utilities.assembly.fact_formatting import read_english_text
from app.utilities.assembly.language_profiles import (
    build_autotest_languages,
    collect_language_profiles,
)
from app.utilities.assembly.language_scenarios import (
    LANGUAGE_SCENARIO_KINDS,
    choose_foreign_languages,
    choose_transliterated_languages,
)
from app.utilities.assembly.owner_check_scenarios import plan_owner_check_scenarios
from app.utilities.assembly.smoke_selection import plan_smoke_scenarios

DEFAULT_PRICE_QUESTION_LIMIT: PriceQuestionScenarioLimit = PriceQuestionScenarioLimit(
    10
)
KNOWLEDGE_KIND_ORDER: list[KnowledgeItemKind] = list(KnowledgeItemKind)


class PlanAutotestScenariosUseCase(
    UseCaseContract[AutotestPlanningRequest, AutotestScenarioPlanning]
):
    """
    Plan the scenarios of an autotest run (concept sections 4 and 11).

    Scenarios are the selected version languages crossed with the niche's
    applicable scenario kinds (booking scenarios only for a version that
    books), the language scenarios (a customer who writes a language the
    version does not list, and one who types a version language in Latin
    letters), plus one price question per priced knowledge item, at most
    `price_question_limit`, and the niche's own booking variants (a named
    master, a room type for several nights) from the business's services
    and rooms, asked in the languages in turn. The plan has full coverage
    when every version language and every applicable kind was selected:
    only such a run can show that a version is ready for customers. The
    quick check of an
    apply (`smoke_check`) plans exactly its scenarios instead and never has
    full coverage. Both end with the owner's own active checks ("My
    checks"), so a corrected answer is checked in every apply: all of them
    in a quick check, those in the selected languages otherwise (none when
    the selected kinds leave out `owner_check`).
    """

    def __init__(
        self,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        autotest_case_repo: AutotestCaseRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        language_registry: LanguageRegistryContract,
        price_question_limit: PriceQuestionScenarioLimit = DEFAULT_PRICE_QUESTION_LIMIT,
    ) -> None:
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._language_registry: LanguageRegistryContract = language_registry
        self._price_question_limit: PriceQuestionScenarioLimit = price_question_limit

    def run(self, input_data: AutotestPlanningRequest) -> AutotestScenarioPlanning:
        business: BusinessDocument = input_data.business
        version: AssistantVersionDocument = input_data.version
        niche: NicheTemplate = self._niche_template_registry.get(version.niche_key)
        applicable_kinds: list[AutotestScenarioKind] = list_applicable_kinds(
            niche.autotest_kinds,
            version.tools,
            version.languages,
        )
        party_size: int = self._party_size(business)
        resource_noun: str = (
            read_english_text(niche.resource_nouns)
            or RESOURCE_KIND_NOUNS[niche.resource_kind]
        )
        if input_data.smoke_check is not None:
            return AutotestScenarioPlanning(
                scenarios=self._plan_smoke_check(
                    input_data.smoke_check,
                    version,
                    applicable_kinds,
                    resource_noun,
                    party_size,
                )
                + self._plan_owner_checks(business, None),
                is_full_coverage=False,
            )

        languages: list[LanguageTag] = select_languages(
            version.languages,
            input_data.languages,
        )
        requested_kinds: list[AutotestScenarioKind] | None = (
            None
            if input_data.kinds is None
            else [
                kind
                for kind in input_data.kinds
                if kind is not AutotestScenarioKind.OWNER_CHECK
            ]
        )
        kinds: list[AutotestScenarioKind] = (
            []
            if requested_kinds == []
            else select_kinds(applicable_kinds, requested_kinds)
        )
        plays_owner_checks: bool = (
            input_data.kinds is None
            or AutotestScenarioKind.OWNER_CHECK in input_data.kinds
        )
        items: list[KnowledgeItemDocument] = self._knowledge_item_repo.list_by_business(
            business.id
        )
        priced_items: list[KnowledgeItemDocument] = sorted(
            (item for item in items if item.is_active and item.price_minor is not None),
            key=lambda item: (
                KNOWLEDGE_KIND_ORDER.index(item.kind),
                str(item.title).casefold(),
                str(item.id),
            ),
        )
        autotest_languages: list[AutotestLanguage] = build_autotest_languages(
            languages,
            collect_language_profiles(self._language_registry, languages),
        )
        variant_goals: list[AutotestScenarioGoal] = (
            plan_variant_goals(
                niche.booking_variants,
                items,
                self._resource_repo.list_by_business(business.id),
            )
            if AutotestScenarioKind.BOOKING in kinds
            else []
        )
        return AutotestScenarioPlanning(
            scenarios=plan_scenarios(
                languages=autotest_languages,
                kinds=[kind for kind in kinds if kind not in LANGUAGE_SCENARIO_KINDS],
                priced_item_titles=[str(item.title) for item in priced_items],
                price_question_limit=int(self._price_question_limit),
                resource_noun=resource_noun,
                party_size=party_size,
            )
            + plan_variant_scenarios(autotest_languages, variant_goals)
            + self._plan_language_scenarios(kinds, version, languages)
            + (
                self._plan_owner_checks(business, languages)
                if plays_owner_checks
                else []
            ),
            is_full_coverage=(
                set(languages) >= set(version.languages)
                and set(kinds) >= set(applicable_kinds)
            ),
        )

    def _plan_language_scenarios(
        self,
        kinds: list[AutotestScenarioKind],
        version: AssistantVersionDocument,
        languages: list[LanguageTag],
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
                languages=build_autotest_languages(
                    kind_languages,
                    collect_language_profiles(self._language_registry, kind_languages),
                ),
                kinds=[kind],
                priced_item_titles=[],
                price_question_limit=0,
                resource_noun="",
                party_size=DEFAULT_PARTY_SIZE,
            )
        ]

    def _plan_owner_checks(
        self,
        business: BusinessDocument,
        languages: list[LanguageTag] | None,
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
        return plan_owner_check_scenarios(
            cases,
            build_autotest_languages(
                case_languages,
                collect_language_profiles(self._language_registry, case_languages),
            ),
        )

    def _party_size(self, business: BusinessDocument) -> int:
        """Two people, or fewer when the booking rules allow fewer."""

        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        if profile is None or profile.booking_rules is None:
            return DEFAULT_PARTY_SIZE

        return min(DEFAULT_PARTY_SIZE, int(profile.booking_rules.max_party_size))

    def _plan_smoke_check(
        self,
        selection: SmokeCheckSelection,
        version: AssistantVersionDocument,
        applicable_kinds: list[AutotestScenarioKind],
        resource_noun: str,
        party_size: int,
    ) -> list[AutotestScenario]:
        """The quick check's scenarios in the version's own languages."""

        languages: list[LanguageTag] = [
            language
            for language in version.languages
            if language == selection.price_language
            or any(pick.language == language for pick in selection.picks)
        ]
        return plan_smoke_scenarios(
            selection,
            build_autotest_languages(
                languages,
                collect_language_profiles(self._language_registry, languages),
            ),
            applicable_kinds,
            resource_noun,
            party_size,
        )
