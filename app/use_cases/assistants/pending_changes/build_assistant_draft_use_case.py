from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import (
    CountryRegistryContract,
    LanguageRegistryContract,
    NicheTemplateRegistryContract,
    PlanRegistryContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.assistants.assembly_sources import (
    AssistantInstructionSource,
    BusinessFactsSource,
)
from app.schemas.dto.assistants.assistant_drafts import (
    AssistantDraft,
    AssistantDraftRequest,
)
from app.schemas.dto.billing import PlanDefinition
from app.schemas.dto.localization import CountryProfile, LanguageProfile
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.utilities.assembly.assistant_tools import (
    can_take_bookings,
    select_assistant_tools,
)
from app.utilities.assembly.fact_formatting import compute_local_date
from app.utilities.assembly.language_profiles import collect_language_profiles


class BuildAssistantDraftUseCase(
    UseCaseContract[AssistantDraftRequest, AssistantDraft]
):
    """
    The assistant as it would be built now (concept section 4,
    "buildAssistant"), without storing anything: the fact table and the
    instructions (chat, and the phone when the plan has voice) are built by
    code from the niche template, the profile, active knowledge items,
    resources and upcoming special days; tools follow the niche (booking
    tools only for a business with booking rules and an active resource,
    send_link only with links) and voice follows the plan.

    Assembling a version stores this draft; the changes not live yet are
    this draft compared with the live version.

    Raises:
        ValidationFailedError: the business has no profile yet.
    """

    def __init__(
        self,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
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
        phone_instruction_transformer: TransformerContract[
            AssistantInstructionSource,
            SystemPromptText,
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
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
        self._phone_instruction_transformer: TransformerContract[
            AssistantInstructionSource,
            SystemPromptText,
        ] = phone_instruction_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AssistantDraftRequest) -> AssistantDraft:
        business: BusinessDocument = input_data.business
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
        # The staff language too: handoff summaries are written in it.
        language_profiles: list[LanguageProfile] = collect_language_profiles(
            self._language_registry,
            list(dict.fromkeys([*business.languages, business.owner_language])),
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
        today: LocalDate = compute_local_date(
            self._wall_clock.now_unix(), business.timezone
        )
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
                today=today,
            )
        )
        tools: list[AssistantToolName] = select_assistant_tools(
            takes_bookings=can_take_bookings(profile, resources),
            has_links=bool(profile.links),
        )
        instruction_source = AssistantInstructionSource(
            business=business,
            profile=profile,
            niche=niche,
            country=country,
            language_profiles=language_profiles,
            facts=facts,
            tools=tools,
            knowledge_items=knowledge_items,
        )
        return AssistantDraft(
            facts=facts,
            tools=tools,
            prompt_text=self._assistant_instruction_transformer.transform(
                instruction_source
            ),
            phone_prompt_text=(
                self._phone_instruction_transformer.transform(instruction_source)
                if plan.is_voice_included
                else None
            ),
            is_voice_enabled=plan.is_voice_included,
            profile_revision=profile.updated_at,
            today=today,
            instruction_source=instruction_source,
        )
