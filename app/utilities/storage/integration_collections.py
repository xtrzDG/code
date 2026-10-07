"""
The catalog entries of the public API and outbound webhooks (1181). Part
of DOCUMENT_COLLECTIONS (document_collection_catalog.py) and
DOCUMENT_LOOKUP_FIELDS (document_lookup_catalog.py).

- webhook_endpoints: the active endpoints an announced change goes to
  (`status`), the cabinet's list in creation order (`created_at`);
- webhook_deliveries: an endpoint's delivery log newest first
  (`endpoint_id`, `created_at`) and, across businesses for the daily
  purge, the deliveries past their 30 days (`expires_at`); a customer's
  deliveries for the erasure of their data (`contact_id`);
- api_keys: across businesses, the key of a request by its digest
  (`secret_hash`, unique), and the cabinet's list (`created_at`).
"""

from collections.abc import Mapping

from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field, text_field

WEBHOOK_ENDPOINTS: DocumentCollectionName = DocumentCollectionName("webhook_endpoints")
WEBHOOK_DELIVERIES: DocumentCollectionName = DocumentCollectionName(
    "webhook_deliveries"
)
API_KEYS: DocumentCollectionName = DocumentCollectionName("api_keys")

INTEGRATION_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(WEBHOOK_ENDPOINTS, WebhookEndpointDocument),
    DocumentCollectionDefinition(WEBHOOK_DELIVERIES, WebhookDeliveryDocument),
    DocumentCollectionDefinition(API_KEYS, ApiKeyDocument),
)

INTEGRATION_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    WEBHOOK_ENDPOINTS: (text_field("status"), integer_field("created_at")),
    WEBHOOK_DELIVERIES: (
        text_field("endpoint_id"),
        integer_field("created_at"),
        integer_field("expires_at"),
        text_field("contact_id"),
    ),
    API_KEYS: (text_field("secret_hash"), integer_field("created_at")),
}
