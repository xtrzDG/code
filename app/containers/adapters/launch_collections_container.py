from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.setup import (
    ActivationEventDocument,
    AssistantApplyDocument,
    SetupStateDocument,
)


class LaunchCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the guided launch (migration 1044): each
    business's milestones, the setup steps it skipped and its current
    "Apply changes". A sibling of DocumentCollectionsContainer with the
    same storage factory (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    activation_event_collection = document_collection(
        ActivationEventDocument,
        "activation_events",
        config,
        clients,
        utilities,
        time_provider,
    )
    setup_state_collection = document_collection(
        SetupStateDocument, "setup_states", config, clients, utilities, time_provider
    )
    assistant_apply_collection = document_collection(
        AssistantApplyDocument,
        "assistant_applies",
        config,
        clients,
        utilities,
        time_provider,
    )
