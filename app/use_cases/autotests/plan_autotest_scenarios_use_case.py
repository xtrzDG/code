from app.contracts.registries import (
    LanguageRegistryContract,
    NicheTemplateRegistryContract,
)
from app.contracts.repositories.business_repositories import BusinessProfileRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.assistants import (
    AutotestPlanningRequest,
    AutotestScenarioPlanning,
)
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.assistants.constrained_integers import (
    PriceQuestionScenarioLimit,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_scenarios import (
    DEFAULT_PARTY_SIZE,
    list_applicable_kinds,
    plan_scenarios,
    select_kinds,
    select_languages,
)
from app.utilities.assembly.fact_descriptions import RESOURCE_KIND_NOUNS
from app.utilities.assembly.fact_formatting import read_english_text
from app.utilities.assembly.language_profiles import (
    build_autotest_languages,
    collect_language_profiles,
)

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
    books), plus one price question per priced knowledge item, at most
    `price_question_limit`. The plan has full coverage when every version
    language and every applicable kind was selected: only such a run can
    show that a version is ready for customers.
    """

    def __init__(
        self,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        language_registry: LanguageRegistryContract,
        price_question_limit: PriceQuestionScenarioLimit = DEFAULT_PRICE_QUESTION_LIMIT,
    ) -> None:
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._language_registry: LanguageRegistryContract = language_registry
        self._price_question_limit: PriceQuestionScenarioLimit = price_question_limit

    def run(self, input_data: AutotestPlanningRequest) -> AutotestScenarioPlanning:
        business: BusinessDocument = input_data.business
        version: AssistantVersionDocument = input_data.version
        niche: NicheTemplate = self._niche_template_registry.get(version.niche_key)
        languages: list[LanguageTag] = select_languages(
            version.languages,
            input_data.languages,
        )
        applicable_kinds: list[AutotestScenarioKind] = list_applicable_kinds(
            niche.autotest_kinds,
            version.tools,
        )
        kinds: list[AutotestScenarioKind] = select_kinds(
            applicable_kinds,
            input_data.kinds,
        )
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        party_size: int = DEFAULT_PARTY_SIZE
        if profile is not None and profile.booking_rules is not None:
            party_size = min(
                DEFAULT_PARTY_SIZE, int(profile.booking_rules.max_party_size)
            )

        priced_items: list[KnowledgeItemDocument] = sorted(
            (
                item
                for item in self._knowledge_item_repo.list_by_business(business.id)
                if item.is_active and item.price_minor is not None
            ),
            key=lambda item: (
                KNOWLEDGE_KIND_ORDER.index(item.kind),
                str(item.title).casefold(),
                str(item.id),
            ),
        )
        return AutotestScenarioPlanning(
            scenarios=plan_scenarios(
                languages=build_autotest_languages(
                    languages,
                    collect_language_profiles(self._language_registry, languages),
                ),
                kinds=kinds,
                priced_item_titles=[str(item.title) for item in priced_items],
                price_question_limit=int(self._price_question_limit),
                resource_noun=(
                    read_english_text(niche.resource_nouns)
                    or RESOURCE_KIND_NOUNS[niche.resource_kind]
                ),
                party_size=party_size,
            ),
            is_full_coverage=(
                set(languages) >= set(version.languages)
                and set(kinds) >= set(applicable_kinds)
            ),
        )
