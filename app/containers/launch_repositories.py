from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.launch_collections_container import (
    LaunchCollectionsContainer,
)
from app.repositories.activation_probe_repository import ActivationProbeRepository
from app.repositories.activation_repositories import (
    NudgeSentRepository,
    OnboardingRequestRepository,
)
from app.repositories.autotest_case_repository import AutotestCaseRepository
from app.repositories.setup_probe_repository import SetupProbeRepository
from app.repositories.setup_repositories import (
    ActivationEventRepository,
    AssistantApplyRepository,
    SetupStateRepository,
)
from app.repositories.sharing_repositories import PublicSlugClaimRepository
from app.repositories.website_import_repository import WebsiteImportRepository


class LaunchRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories over `LaunchCollectionsContainer`: the guided launch
    (1044), the hosted chat addresses (1052) and the current website import
    (1054), the activation follow-up (1080) and the owner's own checks
    (1112). `RepositoriesContainer`
    extends it, so they are read as
    `repositories.setup_state_repo` like every other repository.
    """

    launch_collections: LaunchCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    # The conversations and bookings the guide's probes read.
    probe_collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    # The guided launch: milestones, setup state, the current apply (1044).
    activation_event_repo: Singleton[ActivationEventRepository] = Singleton(
        ActivationEventRepository,
        collection=launch_collections.activation_event_collection,
    )
    setup_state_repo: Singleton[SetupStateRepository] = Singleton(
        SetupStateRepository,
        collection=launch_collections.setup_state_collection,
    )
    assistant_apply_repo: Singleton[AssistantApplyRepository] = Singleton(
        AssistantApplyRepository,
        collection=launch_collections.assistant_apply_collection,
    )
    # Sharing the assistant: the hosted chat addresses (1052).
    public_slug_claim_repo: Singleton[PublicSlugClaimRepository] = Singleton(
        PublicSlugClaimRepository,
        collection=launch_collections.public_slug_claim_collection,
    )
    # The current website import of each business (1054).
    website_import_repo: Singleton[WebsiteImportRepository] = Singleton(
        WebsiteImportRepository,
        collection=launch_collections.website_import_collection,
    )
    # The activation follow-up: nudges sent, done-for-you requests (1080).
    nudge_sent_repo: Singleton[NudgeSentRepository] = Singleton(
        NudgeSentRepository,
        collection=launch_collections.nudge_sent_collection,
    )
    onboarding_request_repo: Singleton[OnboardingRequestRepository] = Singleton(
        OnboardingRequestRepository,
        collection=launch_collections.onboarding_request_collection,
    )
    setup_probe_repo: Singleton[SetupProbeRepository] = Singleton(
        SetupProbeRepository,
        conversation_collection=probe_collections.conversation_collection,
        booking_collection=probe_collections.booking_collection,
    )
    # The owner's own checks ("My checks", 1112).
    autotest_case_repo: Singleton[AutotestCaseRepository] = Singleton(
        AutotestCaseRepository,
        collection=launch_collections.autotest_case_collection,
    )
    # Whether the business reached its activation milestones (1080).
    activation_probe_repo: Singleton[ActivationProbeRepository] = Singleton(
        ActivationProbeRepository,
        conversation_collection=probe_collections.conversation_collection,
        booking_collection=probe_collections.booking_collection,
        handoff_collection=probe_collections.handoff_collection,
    )
