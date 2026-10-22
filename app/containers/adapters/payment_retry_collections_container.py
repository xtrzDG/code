from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument


class PaymentRetryCollectionsContainer(containers.DeclarativeContainer):
    """
    The retries of declined automatic charges (dunning, migration 1214). A
    sibling of DocumentCollectionsContainer with the same storage factory
    (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    payment_retry_attempt_collection = document_collection(
        PaymentRetryAttemptDocument,
        "payment_retry_attempts",
        config,
        clients,
        utilities,
        time_provider,
    )
