from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.domain.client_health_changes import (
    AdminDigestStateDocument,
    ClientHealthChangeDocument,
)
from app.schemas.domain.client_notes import ClientNoteDocument


class ClientCareCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the admin's client care (migration 1143):
    the credit ledger, the platform team's notes, health changes and how far
    each digest has looked. A sibling of DocumentCollectionsContainer with
    the same storage factory (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    billing_credit_collection = document_collection(
        BillingCreditDocument,
        "billing_credits",
        config,
        clients,
        utilities,
        time_provider,
    )
    client_note_collection = document_collection(
        ClientNoteDocument,
        "client_notes",
        config,
        clients,
        utilities,
        time_provider,
    )
    client_health_change_collection = document_collection(
        ClientHealthChangeDocument,
        "client_health_changes",
        config,
        clients,
        utilities,
        time_provider,
    )
    admin_digest_state_collection = document_collection(
        AdminDigestStateDocument,
        "admin_digest_states",
        config,
        clients,
        utilities,
        time_provider,
    )
