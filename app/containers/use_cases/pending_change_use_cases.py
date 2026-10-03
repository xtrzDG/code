from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistants.assistant_drafts import (
    AssistantDraft,
    AssistantDraftRequest,
)
from app.schemas.dto.assistants.smoke_checks import SmokeCheckSelection
from app.schemas.dto.setup.apply_changes import AppliedVersion
from app.schemas.dto.setup.pending_changes import (
    PendingChange,
    PendingChangesQuery,
    PendingChangesRequest,
    PendingChangesView,
)
from app.use_cases.assistants.apply.select_smoke_checks_use_case import (
    SelectSmokeChecksUseCase,
)
from app.use_cases.assistants.pending_changes.build_assistant_draft_use_case import (
    BuildAssistantDraftUseCase,
)
from app.use_cases.assistants.pending_changes.collect_pending_changes_use_case import (
    CollectPendingChangesUseCase,
)
from app.use_cases.assistants.pending_changes.get_pending_changes_use_case import (
    GetPendingChangesUseCase,
)


class PendingChangeUseCasesContainer(containers.DeclarativeContainer):
    """
    The assistant as it would be built now, and how it differs from a
    version: what assembling stores, what "Apply changes" compares and
    checks quickly, and the changes not live yet the cabinet lists.
    """

    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    build_assistant_draft_use_case: Factory[
        UseCaseContract[AssistantDraftRequest, AssistantDraft]
    ] = Factory(
        BuildAssistantDraftUseCase,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        country_registry=registries.country_registry,
        language_registry=registries.language_registry,
        niche_template_registry=registries.niche_template_registry,
        plan_registry=registries.plan_registry,
        business_facts_transformer=transformers.business_facts_transformer,
        assistant_instruction_transformer=transformers.assistant_instruction_transformer,
        phone_instruction_transformer=transformers.phone_instruction_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    collect_pending_changes_use_case: Factory[
        UseCaseContract[PendingChangesRequest, list[PendingChange]]
    ] = Factory(
        CollectPendingChangesUseCase,
        build_assistant_draft=build_assistant_draft_use_case,
        assistant_instruction_transformer=transformers.assistant_instruction_transformer,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    get_pending_changes_use_case: Factory[
        UseCaseContract[PendingChangesQuery, PendingChangesView]
    ] = Factory(
        GetPendingChangesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        business_profile_repo=repositories.business_profile_repo,
        collect_pending_changes=collect_pending_changes_use_case,
    )
    select_smoke_checks_use_case: Factory[
        UseCaseContract[AppliedVersion, SmokeCheckSelection | None]
    ] = Factory(
        SelectSmokeChecksUseCase,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        niche_template_registry=registries.niche_template_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
