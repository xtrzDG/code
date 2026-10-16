from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.web_vitals import WebVitalSampleDocument


class AnalyticsCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the founder's growth analytics (migration
    1074): the owners' product events and the cabinet's Web Vitals. A
    sibling of DocumentCollectionsContainer with the same storage factory
    (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    product_event_collection = document_collection(
        ProductEventDocument,
        "product_events",
        config,
        clients,
        utilities,
        time_provider,
    )
    web_vital_sample_collection = document_collection(
        WebVitalSampleDocument,
        "web_vital_samples",
        config,
        clients,
        utilities,
        time_provider,
    )
