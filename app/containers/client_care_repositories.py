from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.client_care_collections_container import (
    ClientCareCollectionsContainer,
)
from app.containers.referral_repositories import ReferralRepositoriesContainer
from app.repositories.client_care_repositories import (
    AdminDigestStateRepository,
    BillingCreditRepository,
    ClientHealthChangeRepository,
    ClientNoteRepository,
)
from app.repositories.subscription_event_repositories import (
    SubscriptionEventRepository,
)


class ClientCareRepositoriesContainer(ReferralRepositoriesContainer):
    """
    The repositories of the admin's client care (migration 1143) and of
    the subscription lifecycle (1161), on top
    of the referral program's (1150).
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
    subscription_event_repo: Singleton[SubscriptionEventRepository] = Singleton(
        SubscriptionEventRepository,
        collection=client_care_collections.subscription_event_collection,
    )
