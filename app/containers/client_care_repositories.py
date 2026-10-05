from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.client_care_collections_container import (
    ClientCareCollectionsContainer,
)
from app.repositories.client_care_repositories import (
    AdminDigestStateRepository,
    BillingCreditRepository,
    ClientHealthChangeRepository,
    ClientNoteRepository,
)


class ClientCareRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the admin's client care (migration 1143).
    `RepositoriesContainer` extends it, so they are read as
    `repositories.billing_credit_repo` like every other repository.
    """

    client_care_collections: ClientCareCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    billing_credit_repo: Singleton[BillingCreditRepository] = Singleton(
        BillingCreditRepository,
        collection=client_care_collections.billing_credit_collection,
    )
    client_note_repo: Singleton[ClientNoteRepository] = Singleton(
        ClientNoteRepository,
        collection=client_care_collections.client_note_collection,
    )
    client_health_change_repo: Singleton[ClientHealthChangeRepository] = Singleton(
        ClientHealthChangeRepository,
        collection=client_care_collections.client_health_change_collection,
    )
    admin_digest_state_repo: Singleton[AdminDigestStateRepository] = Singleton(
        AdminDigestStateRepository,
        collection=client_care_collections.admin_digest_state_collection,
    )
