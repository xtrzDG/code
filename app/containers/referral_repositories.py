from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.referral_collections_container import (
    ReferralCollectionsContainer,
)
from app.repositories.commission_entry_repository import CommissionEntryRepository
from app.repositories.partner_repository import PartnerRepository
from app.repositories.referral_repositories import (
    ReferralCodeRepository,
    ReferralRepository,
)


class ReferralRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the referral and partner program (migration 1150).
    `ClientCareRepositoriesContainer` extends it (and `RepositoriesContainer`
    that one), so they are read as `repositories.partner_repo` like every
    other repository.
    """

    referral_collections: ReferralCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    partner_repo: Singleton[PartnerRepository] = Singleton(
        PartnerRepository,
        collection=referral_collections.partner_collection,
    )
    referral_code_repo: Singleton[ReferralCodeRepository] = Singleton(
        ReferralCodeRepository,
        collection=referral_collections.referral_code_collection,
    )
    referral_repo: Singleton[ReferralRepository] = Singleton(
        ReferralRepository,
        collection=referral_collections.referral_collection,
    )
    commission_entry_repo: Singleton[CommissionEntryRepository] = Singleton(
        CommissionEntryRepository,
        collection=referral_collections.commission_entry_collection,
    )
