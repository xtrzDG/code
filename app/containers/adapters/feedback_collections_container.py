from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.feedback import FeedbackRequestDocument, ReviewSettingsDocument


class FeedbackCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the feedback after visits (migration
    1062): each business's review settings and the request for feedback
    after each visit. A sibling of DocumentCollectionsContainer with the
    same storage factory (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    review_settings_collection = document_collection(
        ReviewSettingsDocument,
        "review_settings",
        config,
        clients,
        utilities,
        time_provider,
    )
    feedback_request_collection = document_collection(
        FeedbackRequestDocument,
        "feedback_requests",
        config,
        clients,
        utilities,
        time_provider,
    )
