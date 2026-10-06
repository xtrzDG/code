"""The waitlist's entries and the return visits' messages in a full export."""

from collections.abc import Sequence

from base_pydantic_schemas import BaseDocument

from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
)
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.domain.campaigns import CampaignMessageDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.exports.archive_paging import read_all


def growth_documents(
    business_id: BusinessId,
    waitlist_entry_repo: WaitlistEntryRepoContract | None,
    campaign_message_repo: CampaignMessageRepoContract | None,
) -> dict[str, Sequence[BaseDocument]]:
    """The waitlist's entries and the return visits' messages (none: none)."""

    collections: dict[str, Sequence[BaseDocument]] = {}
    if waitlist_entry_repo is not None:
        entries: list[WaitlistEntryDocument] = read_all(
            lambda window: waitlist_entry_repo.page_in_statuses(
                business_id, list(WaitlistStatus), window, is_descending=False
            ),
            lambda entry: int(entry.created_at),
        )
        collections["waitlist_entries"] = entries
    if campaign_message_repo is not None:
        messages: list[CampaignMessageDocument] = read_all(
            lambda window: campaign_message_repo.page_latest(business_id, window),
            lambda message: int(message.created_at),
        )
        collections["campaign_messages"] = messages
    return collections
