from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import (
    LanguageRegistryContract,
    NicheTemplateRegistryContract,
)
from app.contracts.repositories import (
    AssistantVersionRepoContract,
    BusinessProfileRepoContract,
    KnowledgeItemRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants import (
    AutotestRunPlan,
    AutotestScenario,
    RunAutotestsCommand,
)
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.constrained_integers import (
    PriceQuestionScenarioLimit,
)
from app.schemas.typings.assistants.prefixed_id import AutotestRunId
from app.utilities.assembly.autotest_scenarios import (
    DEFAULT_PARTY_SIZE,
    list_applicable_kinds,
    plan_scenarios,
    select_kinds,
    select_languages,
)
from app.utilities.assembly.fact_descriptions import RESOURCE_KIND_NOUNS
from app.utilities.assembly.fact_formatting import (
    find_example_mobile_number,
    read_english_text,
)
from app.utilities.assembly.language_profiles import (
    build_autotest_languages,
    collect_language_profiles,
)

DEFAULT_PRICE_QUESTION_LIMIT: PriceQuestionScenarioLimit = PriceQuestionScenarioLimit(
    10
)
UNTESTABLE_STATUSES: frozenset[AssistantVersionStatus] = frozenset(
    {AssistantVersionStatus.PUBLISHED, AssistantVersionStatus.ARCHIVED}
)
KNOWLEDGE_KIND_ORDER: list[KnowledgeItemKind] = list(KnowledgeItemKind)


class StartAutotestRunUseCase(UseCaseContract[RunAutotestsCommand, AutotestRunPlan]):
    """
    Owner starts the autotests of a version (concept sections 4 and 11).

    Scenarios are the selected version languages crossed with the niche's
    applicable scenario kinds (booking scenarios only for a version that
    books), plus one price question per priced knowledge item, at most
    `price_question_limit`. The version moves to TESTING. Live and archived
    versions are not re-tested, because that would change their status.
    The AI customer gets a valid example mobile number of the business
    country, so bookings work for any country.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        language_registry: LanguageRegistryContract,
        wall_clock: WallClock[Microseconds],
        price_question_limit: PriceQuestionScenarioLimit = DEFAULT_PRICE_QUESTION_LIMIT,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._language_registry: LanguageRegistryContract = language_registry
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._price_question_limit: PriceQuestionScenarioLimit = price_question_limit

    def run(self, input_data: RunAutotestsCommand) -> AutotestRunPlan:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id,
            input_data.version_id,
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {input_data.version_id} was not found."
            )

        if version.status in UNTESTABLE_STATUSES:
            raise ConflictError(
                f"Version {version.version_number} is {version.status.value}; "
                "assemble a new version to test changes."
            )

        scenarios: list[AutotestScenario] = self._plan(business, version, input_data)
        if not scenarios:
            raise ValidationFailedError("There are no autotest scenarios to run.")

        now: Microseconds = self._wall_clock.now_unix()
        version.status = AssistantVersionStatus.TESTING
        version.updated_at = now
        self._assistant_version_repo.save(version)
        return AutotestRunPlan(
            run_id=AutotestRunId(),
            business=business,
            version=version,
            scenarios=scenarios,
            customer_phone_number=find_example_mobile_number(business.country_code),
            started_at=now,
        )

    def _plan(
        self,
        business: BusinessDocument,
        version: AssistantVersionDocument,
        command: RunAutotestsCommand,
    ) -> list[AutotestScenario]:
        niche: NicheTemplate = self._niche_template_registry.get(version.niche_key)
        languages = select_languages(version.languages, command.languages)
        kinds = select_kinds(
            list_applicable_kinds(niche.autotest_kinds, version.tools),
            command.kinds,
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
        return plan_scenarios(
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
        )
