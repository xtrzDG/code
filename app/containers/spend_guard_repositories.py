from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.spend_guard_collections_container import (
    SpendGuardCollectionsContainer,
)
from app.repositories.spend_guard_repositories import (
    BusinessLimitsRepository,
    SpendLimitMarkRepository,
    UsageSpendRepository,
)


class SpendGuardRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the spend guard (migration 1142): each business's
    limits, the marks of the days it passed one, and spend summed from the
    usage events. `RepositoriesContainer` extends it, so they are read as
    `repositories.business_limits_repo` like every other repository.
    """

    spend_guard_collections: SpendGuardCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    usage_collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    business_limits_repo: Singleton[BusinessLimitsRepository] = Singleton(
        BusinessLimitsRepository,
        collection=spend_guard_collections.business_limits_collection,
    )
    spend_limit_mark_repo: Singleton[SpendLimitMarkRepository] = Singleton(
        SpendLimitMarkRepository,
        collection=spend_guard_collections.spend_limit_mark_collection,
    )
    usage_spend_repo: Singleton[UsageSpendRepository] = Singleton(
        UsageSpendRepository,
        collection=usage_collections.usage_event_collection,
    )
