"""The demo business's waitlist and return visits, stored with its activity."""

from dataclasses import dataclass

from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
    CampaignSettingsRepoContract,
)
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.schemas.dto.demo_data import DemoBusinessActivity


@dataclass(frozen=True)
class DemoGrowthStore:
    """Writes the activity's waitlist entries, campaign settings and messages."""

    waitlist_entry_repo: WaitlistEntryRepoContract
    campaign_settings_repo: CampaignSettingsRepoContract
    campaign_message_repo: CampaignMessageRepoContract

    def store(self, activity: DemoBusinessActivity) -> None:
        for entry in activity.waitlist_entries:
            self.waitlist_entry_repo.save(entry)
        if activity.campaign_settings is not None:
            self.campaign_settings_repo.save(activity.campaign_settings)
        for message in activity.campaign_messages:
            self.campaign_message_repo.insert_if_new(message)
