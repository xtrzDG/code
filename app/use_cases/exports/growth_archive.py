"""The waitlist's entries and the return visits' messages in a full export."""

from collections.abc import Iterator

from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
)
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.schemas.domain.campaigns import CampaignMessageDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.exports.archive_pages import DocumentPages, pages_in_write_order


def growth_pages(
    business_id: BusinessId,
    waitlist_entry_repo: WaitlistEntryRepoContract | None,
    campaign_message_repo: CampaignMessageRepoContract | None,
) -> dict[str, DocumentPages]:
    """
    The waitlist's entries and the return visits' messages, each read a
    keyset page at a time when its file is written (none: none).
    """

    collections: dict[str, DocumentPages] = {}
    if waitlist_entry_repo is not None:
        entries: Iterator[list[WaitlistEntryDocument]] = pages_in_write_order(
            waitlist_entry_repo, business_id, lambda entry: str(entry.id)
        )
        collections["waitlist_entries"] = entries
    if campaign_message_repo is not None:
        messages: Iterator[list[CampaignMessageDocument]] = pages_in_write_order(
            campaign_message_repo, business_id, lambda message: str(message.id)
        )
        collections["campaign_messages"] = messages
    return collections
