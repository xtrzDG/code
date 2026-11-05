from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.business_limits import (
    BusinessLimitsDocument,
    SpendLimitMarkDocument,
)


class SpendGuardCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the spend guard (migration 1142): each
    business's limits and the marks of the days it passed one. A sibling of
    DocumentCollectionsContainer with the same storage factory (Postgres
    with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    business_limits_collection = document_collection(
        BusinessLimitsDocument,
        "business_limits",
        config,
        clients,
        utilities,
        time_provider,
    )
    spend_limit_mark_collection = document_collection(
        SpendLimitMarkDocument,
        "spend_limit_marks",
        config,
        clients,
        utilities,
        time_provider,
    )
