from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.legal import (
    SubprocessorAnnouncementDocument,
    SubprocessorNoticeDocument,
)


class LegalCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the sub-processor change notices (migration
    1124): each business's notices and each change's announcement. A
    sibling of DocumentCollectionsContainer with the same storage factory
    (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    subprocessor_notice_collection = document_collection(
        SubprocessorNoticeDocument,
        "subprocessor_notices",
        config,
        clients,
        utilities,
        time_provider,
    )
    subprocessor_announcement_collection = document_collection(
        SubprocessorAnnouncementDocument,
        "subprocessor_announcements",
        config,
        clients,
        utilities,
        time_provider,
    )
