from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import (
    CountryRegistryContract,
    LanguageRegistryContract,
    NicheTemplateRegistryContract,
    PlanRegistryContract,
)
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument, BusinessFact
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.assembly_sources import (
    AssistantInstructionSource,
    BusinessFactsSource,
)
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    AssembleAssistantVersionRequest,
)
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.localization import CountryProfile, LanguageProfile
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.strings import SystemPromptText
from app.utilities.assembly.assistant_tools import (
    can_take_bookings,
    select_assistant_tools,
)
from app.utilities.assembly.autotest_scenarios import (
    list_applicable_kinds,
    select_kinds,
    select_languages,
)
from app.utilities.assembly.fact_formatting import compute_local_date
from app.utilities.assembly.language_profiles import collect_language_profiles


class AssembleAssistantVersionUseCase(
    UseCaseContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
):
    """
    Owner assembles a new assistant version from the current profile
    (concept section 4, "buildAssistant").

    The fact table and the instruction are built by code from the niche
    template, the profile, active knowledge items, resources and upcoming
    special days; tools follow the niche (booking tools only for a business
    with booking rules and an active resource, send_link only with links)
    and voice follows the plan. The version gets the next number, the
    configured chat model, status DRAFT and the profile's revision. Every
    edit creates a new version; nothing is changed in place. A business
    still onboarding moves to TESTING.

    Autotest languages and kinds in the request are validated here, before
    anything is stored, so a later autotest phase cannot fail on them.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        country_registry: CountryRegistryContract,
        language_registry: LanguageRegistryContract,
        niche_template_registry: NicheTemplateRegistryContract,
        plan_registry: PlanRegistryContract,
        business_facts_transformer: TransformerContract[
            BusinessFactsSource,
            list[BusinessFact],
        ],
        assistant_instruction_transformer: TransformerContract[
            AssistantInstructionSource,
            SystemPromptText,
        ],
        version_details_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionDetails,
        ],
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._country_registry: CountryRegistryContract = country_registry
        self._language_registry: LanguageRegistryContract = language_registry
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._plan_registry: PlanRegistryContract = plan_registry
        self._business_facts_transformer: TransformerContract[
            BusinessFactsSource,
            list[BusinessFact],
        ] = business_facts_transformer
        self._assistant_instruction_transformer: TransformerContract[
            AssistantInstructionSource,
            SystemPromptText,
        ] = assistant_instruction_transformer
        self._version_details_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionDetails,
        ] = version_details_transformer
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self, input_data: AssembleAssistantVersionCommand
    ) -> AssistantVersionDetails:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        if profile is None:
            raise ValidationFailedError(
                "Fill in the business profile before assembling the assistant."
            )

        niche: NicheTemplate = self._niche_template_registry.get(business.niche_key)
        country: CountryProfile = self._country_registry.get(business.country_code)
        plan: PlanDefinition = self._plan_registry.get(business.plan_key)
        language_profiles: list[LanguageProfile] = collect_language_profiles(
            self._language_registry,
            business.languages,
        )
        knowledge_items: list[KnowledgeItemDocument] = [
            item
            for item in self._knowledge_item_repo.list_by_business(business.id)
            if item.is_active
        ]
        resources: list[ResourceDocument] = [
            resource
            for resource in self._resource_repo.list_by_business(business.id)
            if resource.is_active
        ]
        now: Microseconds = self._wall_clock.now_unix()
        facts: list[BusinessFact] = self._business_facts_transformer.transform(
            BusinessFactsSource(
                business=business,
                profile=profile,
                niche=niche,
                country=country,
                language_profiles=language_profiles,
                knowledge_items=knowledge_items,
                resources=resources,
                schedule_exceptions=self._schedule_exception_repo.list_by_business(
                    business.id
                ),
                today=compute_local_date(now, business.timezone),
            )
        )
        tools: list[AssistantToolName] = select_assistant_tools(
            takes_bookings=can_take_bookings(profile, resources),
            has_links=bool(profile.links),
        )
        self._validate_autotest_selection(input_data.request, business, niche, tools)
        prompt_text: SystemPromptText = (
            self._assistant_instruction_transformer.transform(
                AssistantInstructionSource(
                    business=business,
                    profile=profile,
                    niche=niche,
                    country=country,
                    language_profiles=language_profiles,
                    facts=facts,
                    tools=tools,
                )
            )
        )
        version = AssistantVersionDocument(
            business_id=business.id,
            version_number=self._next_version_number(business),
            status=AssistantVersionStatus.DRAFT,
            niche_key=business.niche_key,
            model_id=self._app_settings.llm_model_id,
            prompt_text=prompt_text,
            tools=tools,
            languages=list(business.languages),
            default_language=business.default_language,
            is_voice_enabled=plan.is_voice_included,
            facts=facts,
            profile_revision=profile.updated_at,
            created_at=now,
            updated_at=now,
        )
        self._assistant_version_repo.save(version)
        if business.status is BusinessStatus.ONBOARDING:

            def start_testing(current: BusinessDocument) -> None:
                # Changed on the business as stored now, so an edit saved
                # while the version was built is kept.
                if current.status is BusinessStatus.ONBOARDING:
                    current.status = BusinessStatus.TESTING
                    current.updated_at = now

            self._business_repo.update(business.id, start_testing)

        return self._version_details_transformer.transform(version)

    def _next_version_number(
        self, business: BusinessDocument
    ) -> AssistantVersionNumber:
        existing_numbers: list[int] = [
            int(version.version_number)
            for version in self._assistant_version_repo.list_by_business(business.id)
        ]
        return AssistantVersionNumber(max(existing_numbers, default=0) + 1)

    def _validate_autotest_selection(
        self,
        request: AssembleAssistantVersionRequest,
        business: BusinessDocument,
        niche: NicheTemplate,
        tools: list[AssistantToolName],
    ) -> None:
        select_languages(business.languages, request.languages)
        select_kinds(list_applicable_kinds(niche.autotest_kinds, tools), request.kinds)
