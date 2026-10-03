from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.launch_collections_container import (
    LaunchCollectionsContainer,
)
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
    (1054). `RepositoriesContainer` extends it, so they are read as
    `repositories.setup_state_repo` like every other repository.
    """

    launch_collections: LaunchCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

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
