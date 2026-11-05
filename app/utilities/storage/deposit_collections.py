"""
The catalog entries of deposits and prepayment links (1190). Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py) and
DOCUMENT_LOOKUP_FIELDS (document_lookup_catalog.py).

- deposit_settings: one document per business, read by id;
- deposit_requests: the deposit of a booking or a banquet request
  (`booking_id`, `lead_id`), and, across businesses for the minute's
  sweep, holds that ran out (`status`, `hold_expires_at`), reminders due
  (`reminder_due_at`) and paid deposits whose cancelled booking is to be
  settled (`settle_after`); the reports' sums of a period by the payment
  (`paid_at`) and the request (`requested_at`), per currency, with the
  amounts summed by the database (`amount_minor`).
"""

from collections.abc import Mapping

from app.schemas.domain.deposits import DepositRequestDocument, DepositSettingsDocument
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

DEPOSIT_SETTINGS: DocumentCollectionName = DocumentCollectionName("deposit_settings")
DEPOSIT_REQUESTS: DocumentCollectionName = DocumentCollectionName("deposit_requests")

DEPOSIT_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(DEPOSIT_SETTINGS, DepositSettingsDocument),
    DocumentCollectionDefinition(DEPOSIT_REQUESTS, DepositRequestDocument),
)

DEPOSIT_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    DEPOSIT_REQUESTS: (
        text_field("booking_id"),
        text_field("lead_id"),
        text_field("status"),
        integer_field("hold_expires_at"),
        integer_field("reminder_due_at"),
        integer_field("settle_after"),
        integer_field("paid_at"),
        integer_field("requested_at"),
        integer_field("amount_minor"),
        # The reports' sums per currency, without the owner's test chats.
        filter_field("currency_code"),
        filter_field("is_sandbox"),
    ),
}
