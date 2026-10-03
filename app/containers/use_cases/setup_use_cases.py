from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.apply_use_cases import ApplyUseCasesContainer
from app.containers.use_cases.assistant_use_cases import AssistantUseCasesContainer
from app.containers.use_cases.launch_use_cases import LaunchUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatCommand
from app.schemas.dto.profiles.business_profile import BusinessProfileView
from app.schemas.dto.setup.profile_patch import PatchProfileCommand
from app.schemas.dto.setup.setup_progress import (
    ActivationMilestoneCheck,
    ActivationMilestoneView,
    CelebrateMilestoneCommand,
    SetupQuery,
    SetupView,
    SkipSetupStepCommand,
)
from app.schemas.dto.setup.starter_answers import (
    ApplyStarterAnswersCommand,
    StarterAnswersApplied,
    StarterAnswersQuery,
    StarterAnswersView,
)
from app.use_cases.setup.apply_starter_answers_use_case import (
    ApplyStarterAnswersUseCase,
)
from app.use_cases.setup.celebrate_milestone_use_case import (
    CelebrateMilestoneUseCase,
)
from app.use_cases.setup.get_setup_progress_use_case import GetSetupProgressUseCase
from app.use_cases.setup.get_starter_answers_use_case import (
    GetStarterAnswersUseCase,
)
from app.use_cases.setup.patch_profile_use_case import PatchProfileUseCase
from app.use_cases.setup.prepare_test_chat_version_use_case import (
    PrepareTestChatVersionUseCase,
)
from app.use_cases.setup.record_activation_milestones_use_case import (
    RecordActivationMilestonesUseCase,
)
from app.use_cases.setup.skip_setup_step_use_case import SkipSetupStepUseCase


class SetupUseCasesContainer(containers.DeclarativeContainer):
    """
    The guided setup: its progress and steps, the niche's starter answers,
    the profile autosave, the test chat's preview version and the
    milestones on the way to live customers.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    assistant_use_cases: AssistantUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    apply_use_cases: ApplyUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    launch_use_cases: LaunchUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_starter_answers_use_case: Factory[
        UseCaseContract[StarterAnswersQuery, StarterAnswersView]
    ] = Factory(
        GetStarterAnswersUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        niche_template_registry=registries.niche_template_registry,
        starter_answer_registry=registries.starter_answer_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    apply_starter_answers_use_case: Factory[
        UseCaseContract[ApplyStarterAnswersCommand, StarterAnswersApplied]
    ] = Factory(
        ApplyStarterAnswersUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        audit_log_repo=repositories.audit_log_repo,
        niche_template_registry=registries.niche_template_registry,
        starter_answer_registry=registries.starter_answer_registry,
        localized_text_resolver=utilities.localized_text_resolver,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    patch_profile_use_case: Factory[
        UseCaseContract[PatchProfileCommand, BusinessProfileView]
    ] = Factory(
        PatchProfileUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_profile_repo=repositories.business_profile_repo,
        audit_log_repo=repositories.audit_log_repo,
        niche_template_registry=registries.niche_template_registry,
        phone_number_parser=utilities.phone_number_parser,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_activation_milestones_use_case: Factory[
        UseCaseContract[ActivationMilestoneCheck, None]
    ] = Factory(
        RecordActivationMilestonesUseCase,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        activation_event_repo=repositories.activation_event_repo,
        activation_probe_repo=repositories.activation_probe_repo,
        record_activation_event=launch_use_cases.record_activation_event_use_case,
    )
    get_setup_progress_use_case: Factory[UseCaseContract[SetupQuery, SetupView]] = (
        Factory(
            GetSetupProgressUseCase,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            record_activation_milestones=record_activation_milestones_use_case,
            describe_apply_changes=apply_use_cases.describe_apply_changes_use_case,
            business_profile_repo=repositories.business_profile_repo,
            knowledge_item_repo=repositories.knowledge_item_repo,
            resource_repo=repositories.resource_repo,
            channel_repo=repositories.channel_repo,
            subscription_repo=repositories.subscription_repo,
            dpa_acceptance_repo=repositories.dpa_acceptance_repo,
            activation_event_repo=repositories.activation_event_repo,
            setup_state_repo=repositories.setup_state_repo,
            niche_template_registry=registries.niche_template_registry,
            plan_registry=registries.plan_registry,
            localized_text_resolver=utilities.localized_text_resolver,
            app_settings=config.app_settings,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    skip_setup_step_use_case: Factory[
        UseCaseContract[SkipSetupStepCommand, SetupView]
    ] = Factory(
        SkipSetupStepUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        setup_state_repo=repositories.setup_state_repo,
        get_setup_progress=get_setup_progress_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
        product_events=facilitators.product_events,
    )
    celebrate_milestone_use_case: Factory[
        UseCaseContract[CelebrateMilestoneCommand, ActivationMilestoneView]
    ] = Factory(
        CelebrateMilestoneUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        record_activation_milestones=record_activation_milestones_use_case,
        activation_event_repo=repositories.activation_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    prepare_test_chat_version_use_case: Factory[
        UseCaseContract[OwnerTestChatCommand, None]
    ] = Factory(
        PrepareTestChatVersionUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assemble_assistant_version=assistant_use_cases.assemble_assistant_version_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
    )
