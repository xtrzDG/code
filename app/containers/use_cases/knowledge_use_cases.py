from typing import cast

from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Dependency, Factory

from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    PriceLookupQuery,
    PriceLookupResult,
    SendLinkQuery,
    SendLinkResult,
)
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    DeleteKnowledgeItemCommand,
    KnowledgeItemDeletion,
    KnowledgeItemDetails,
    KnowledgeItemList,
    KnowledgeItemListQuery,
    KnowledgeItemPage,
    KnowledgeItemQuery,
    UpdateKnowledgeItemCommand,
    UpsertKnowledgeItemsCommand,
)
from app.schemas.dto.knowledge_aliases import SuggestKnowledgeAliasesCommand
from app.schemas.dto.profiles.business_profile import (
    BusinessProfileQuery,
    BusinessProfileView,
    SaveProfileCommand,
)
from app.schemas.dto.profiles.niche_catalog import (
    NicheCatalogQuery,
    NicheCatalogView,
    NicheDetailsView,
    NicheTemplateQuery,
)
from app.schemas.dto.profiles.profile_gaps import ProfileGapsQuery, ProfileGapsView
from app.schemas.dto.profiles.profile_steps import (
    ProfileStepSaveResult,
    SaveProfileStepCommand,
)
from app.schemas.dto.profiles.profile_wizard import (
    ProfileWizardQuery,
    ProfileWizardView,
)
from app.use_cases.knowledge.create_knowledge_item_use_case import (
    CreateKnowledgeItemUseCase,
)
from app.use_cases.knowledge.delete_knowledge_item_use_case import (
    DeleteKnowledgeItemUseCase,
)
from app.use_cases.knowledge.get_knowledge_item_use_case import GetKnowledgeItemUseCase
from app.use_cases.knowledge.get_price_use_case import GetPriceUseCase
from app.use_cases.knowledge.list_knowledge_items_use_case import (
    ListKnowledgeItemsUseCase,
)
from app.use_cases.knowledge.send_link_use_case import SendLinkUseCase
from app.use_cases.knowledge.update_knowledge_item_use_case import (
    UpdateKnowledgeItemUseCase,
)
from app.use_cases.knowledge.upsert_knowledge_items_use_case import (
    UpsertKnowledgeItemsUseCase,
)
from app.use_cases.profiles.compute_profile_gaps_use_case import (
    ComputeProfileGapsUseCase,
)
from app.use_cases.profiles.get_business_profile_use_case import (
    GetBusinessProfileUseCase,
)
from app.use_cases.profiles.get_niche_template_use_case import GetNicheTemplateUseCase
from app.use_cases.profiles.get_profile_wizard_use_case import GetProfileWizardUseCase
from app.use_cases.profiles.list_niche_templates_use_case import (
    ListNicheTemplatesUseCase,
)
from app.use_cases.profiles.save_profile_step_use_case import SaveProfileStepUseCase
from app.use_cases.profiles.save_profile_use_case import SaveProfileUseCase

# The use cases knowledge across languages adds (knowledge_search_use_cases).
type KnowledgeSearch = UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
type AliasSuggestion = UseCaseContract[
    SuggestKnowledgeAliasesCommand, KnowledgeItemDetails
]
type KnowledgeIndexing = UseCaseContract[QueuedJobInput, JobReport]


class KnowledgeUseCasesContainer(containers.DeclarativeContainer):
    """
    What the assistant knows: niche templates, the profile wizard and the
    knowledge base (search_knowledge, get_price and send_link are also tools of
    the conversation engine).
    """

    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Typed edges CoreUseCasesContainer fills (knowledge_search_edges): the
    # job queue edits queue `index_knowledge` on, and knowledge across
    # languages (the search tool, aliases on request, the indexing job).
    job_queue: Dependency[JobQueueFacilitator] = Dependency(
        instance_of=JobQueueFacilitator
    )
    # Use case contracts are protocols, which `instance_of` cannot check at
    # run time: these edges are typed instead of checked.
    search_knowledge_use_case: Dependency[KnowledgeSearch] = cast(
        Dependency[KnowledgeSearch], Dependency()
    )
    suggest_knowledge_aliases_use_case: Dependency[AliasSuggestion] = cast(
        Dependency[AliasSuggestion], Dependency()
    )
    index_knowledge_use_case: Dependency[KnowledgeIndexing] = cast(
        Dependency[KnowledgeIndexing], Dependency()
    )

    # --- Niche templates and the profile wizard.
    list_niche_templates_use_case: Factory[
        UseCaseContract[NicheCatalogQuery, NicheCatalogView]
    ] = Factory(
        ListNicheTemplatesUseCase,
        niche_template_registry=registries.niche_template_registry,
        localized_text_resolver=utilities.localized_text_resolver,
        niche_value_registry=registries.niche_value_registry,
    )
    get_niche_template_use_case: Factory[
        UseCaseContract[NicheTemplateQuery, NicheDetailsView]
    ] = Factory(
        GetNicheTemplateUseCase,
        niche_template_registry=registries.niche_template_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    get_profile_wizard_use_case: Factory[
        UseCaseContract[ProfileWizardQuery, ProfileWizardView]
    ] = Factory(
        GetProfileWizardUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        niche_template_registry=registries.niche_template_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    get_business_profile_use_case: Factory[
        UseCaseContract[BusinessProfileQuery, BusinessProfileView]
    ] = Factory(
        GetBusinessProfileUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
    )
    save_profile_step_use_case: Factory[
        UseCaseContract[SaveProfileStepCommand, ProfileStepSaveResult]
    ] = Factory(
        SaveProfileStepUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        audit_log_repo=repositories.audit_log_repo,
        niche_template_registry=registries.niche_template_registry,
        phone_number_parser=utilities.phone_number_parser,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    save_profile_use_case: Factory[
        UseCaseContract[SaveProfileCommand, BusinessProfileView]
    ] = Factory(
        SaveProfileUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        audit_log_repo=repositories.audit_log_repo,
        niche_template_registry=registries.niche_template_registry,
        phone_number_parser=utilities.phone_number_parser,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    compute_profile_gaps_use_case: Factory[
        UseCaseContract[ProfileGapsQuery, ProfileGapsView]
    ] = Factory(
        ComputeProfileGapsUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        niche_template_registry=registries.niche_template_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )

    # --- Knowledge base (search_knowledge, get_price and send_link are tools).
    create_knowledge_item_use_case: Factory[
        UseCaseContract[CreateKnowledgeItemCommand, KnowledgeItemDetails]
    ] = Factory(
        CreateKnowledgeItemUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        niche_template_registry=registries.niche_template_registry,
        wall_clock=time_provider.microsecond_wall_clock,
        job_queue=job_queue,
    )
    get_knowledge_item_use_case: Factory[
        UseCaseContract[KnowledgeItemQuery, KnowledgeItemDetails]
    ] = Factory(
        GetKnowledgeItemUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
    )
    list_knowledge_items_use_case: Factory[
        UseCaseContract[KnowledgeItemListQuery, KnowledgeItemPage]
    ] = Factory(
        ListKnowledgeItemsUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        data_task_registry=registries.data_task_registry,
        data_task_state_repo=repositories.data_task_state_repo,
    )
    update_knowledge_item_use_case: Factory[
        UseCaseContract[UpdateKnowledgeItemCommand, KnowledgeItemDetails]
    ] = Factory(
        UpdateKnowledgeItemUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        niche_template_registry=registries.niche_template_registry,
        wall_clock=time_provider.microsecond_wall_clock,
        job_queue=job_queue,
    )
    delete_knowledge_item_use_case: Factory[
        UseCaseContract[DeleteKnowledgeItemCommand, KnowledgeItemDeletion]
    ] = Factory(
        DeleteKnowledgeItemUseCase,
        knowledge_item_repo=repositories.knowledge_item_repo,
        job_queue=job_queue,
    )
    upsert_knowledge_items_use_case: Factory[
        UseCaseContract[UpsertKnowledgeItemsCommand, KnowledgeItemList]
    ] = Factory(
        UpsertKnowledgeItemsUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        niche_template_registry=registries.niche_template_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_price_use_case: Factory[
        UseCaseContract[PriceLookupQuery, PriceLookupResult]
    ] = Factory(
        GetPriceUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
    )
    send_link_use_case: Factory[UseCaseContract[SendLinkQuery, SendLinkResult]] = (
        Factory(
            SendLinkUseCase,
            business_profile_repo=repositories.business_profile_repo,
        )
    )
