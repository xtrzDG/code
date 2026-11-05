from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.growth_collections_container import (
    GrowthCollectionsContainer,
)
from app.repositories.campaign_repositories import (
    CampaignMessageRepository,
    CampaignSettingsRepository,
)
from app.repositories.deposit_repositories import (
    DepositRequestRepository,
    DepositSettingsRepository,
)
from app.repositories.waitlist_repositories import (
    WaitlistEntryRepository,
    WaitlistSettingsRepository,
)


class GrowthRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the revenue features (migration 1151): the waitlist,
    the rebooking campaigns (the counts of the bookings they brought are
    with the value repositories: `origin_booking_count_repo`), and the
    deposits (1190; the bookings' outcomes they compare are with the value
    repositories too: `booking_outcome_repo`).
    `RepositoriesContainer` extends it, so they are read as
    `repositories.waitlist_entry_repo` like every other repository.
    """

    growth_collections: GrowthCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    waitlist_entry_repo: Singleton[WaitlistEntryRepository] = Singleton(
        WaitlistEntryRepository,
        collection=growth_collections.waitlist_entry_collection,
    )
    waitlist_settings_repo: Singleton[WaitlistSettingsRepository] = Singleton(
        WaitlistSettingsRepository,
        collection=growth_collections.waitlist_settings_collection,
    )
    campaign_settings_repo: Singleton[CampaignSettingsRepository] = Singleton(
        CampaignSettingsRepository,
        collection=growth_collections.campaign_settings_collection,
    )
    campaign_message_repo: Singleton[CampaignMessageRepository] = Singleton(
        CampaignMessageRepository,
        collection=growth_collections.campaign_message_collection,
    )
    deposit_settings_repo: Singleton[DepositSettingsRepository] = Singleton(
        DepositSettingsRepository,
        collection=growth_collections.deposit_settings_collection,
    )
    deposit_request_repo: Singleton[DepositRequestRepository] = Singleton(
        DepositRequestRepository,
        collection=growth_collections.deposit_request_collection,
    )
