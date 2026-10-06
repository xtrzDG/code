"""
The catalog entries of the revenue features (1151): the waitlist and the
rebooking campaigns. Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py) and DOCUMENT_LOOKUP_FIELDS
(document_lookup_catalog.py).

- waitlist_entries: a customer's open entries (`contact_id`, `status`),
  the cabinet's list by status in join order (`created_at`), and, across
  businesses for the sweep, offers whose hold ran out
  (`offer_expires_at`) and entries whose day passed (`waits_until`);
- waitlist_settings, campaign_settings: one document per business, read
  by id; the campaign job finds the businesses that turned it on across
  businesses (`is_enabled`);
- campaign_messages: a customer's invitations still waiting for a booking
  (`contact_id`, `status`, `sent_at`), the monthly cap's count (`month`),
  the cabinet's latest first (`created_at`).
"""

from collections.abc import Mapping

from app.schemas.domain.campaigns import (
    CampaignMessageDocument,
    CampaignSettingsDocument,
)
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistSettingsDocument
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import (
    filter_field,
    integer_field,
    text_field,
)

WAITLIST_ENTRIES: DocumentCollectionName = DocumentCollectionName("waitlist_entries")
WAITLIST_SETTINGS: DocumentCollectionName = DocumentCollectionName("waitlist_settings")
CAMPAIGN_SETTINGS: DocumentCollectionName = DocumentCollectionName("campaign_settings")
CAMPAIGN_MESSAGES: DocumentCollectionName = DocumentCollectionName("campaign_messages")

GROWTH_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(WAITLIST_ENTRIES, WaitlistEntryDocument),
    DocumentCollectionDefinition(WAITLIST_SETTINGS, WaitlistSettingsDocument),
    DocumentCollectionDefinition(CAMPAIGN_SETTINGS, CampaignSettingsDocument),
    DocumentCollectionDefinition(CAMPAIGN_MESSAGES, CampaignMessageDocument),
)

GROWTH_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    WAITLIST_ENTRIES: (
        text_field("contact_id"),
        text_field("status"),
        integer_field("created_at"),
        integer_field("offer_expires_at"),
        integer_field("waits_until"),
        # The cabinet's lists and counts leave the owner's test chats out.
        filter_field("is_sandbox"),
    ),
    CAMPAIGN_SETTINGS: (text_field("is_enabled"),),
    CAMPAIGN_MESSAGES: (
        text_field("contact_id"),
        text_field("status"),
        text_field("month"),
        integer_field("sent_at"),
        integer_field("created_at"),
    ),
}
