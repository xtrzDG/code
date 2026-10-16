from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.billing_profiles import (
    BillingProfileDocument,
    InvoiceCounterDocument,
)


class InvoicingCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of invoicing (migration 1114): each
    business's billing details and the seller's yearly invoice counters. A
    sibling of DocumentCollectionsContainer with the same storage factory
    (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    billing_profile_collection = document_collection(
        BillingProfileDocument,
        "billing_profiles",
        config,
        clients,
        utilities,
        time_provider,
    )
    invoice_counter_collection = document_collection(
        InvoiceCounterDocument,
        "invoice_counters",
        config,
        clients,
        utilities,
        time_provider,
    )
