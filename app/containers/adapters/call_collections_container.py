from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument


class CallCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of what follows a phone call (migration
    1051): callers who did not get through with their text-backs, and each
    business's call settings. A sibling of DocumentCollectionsContainer
    with the same storage factory (Postgres with DATABASE_URL, else in
    memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    missed_call_collection = document_collection(
        MissedCallDocument,
        "missed_calls",
        config,
        clients,
        utilities,
        time_provider,
    )
    call_settings_collection = document_collection(
        CallSettingsDocument,
        "call_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
