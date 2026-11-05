"""
The catalog entries of the subscription lifecycle (1161): the steps of a
subscription's life, read per business (the pause cap, the win-back
stages) and by kind and time across businesses (the founder's churn
metrics, the win-back job's cancellations). Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py) and DOCUMENT_LOOKUP_FIELDS
(document_lookup_catalog.py).
"""

from collections.abc import Mapping

from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field, text_field

SUBSCRIPTION_EVENTS: DocumentCollectionName = DocumentCollectionName(
    "subscription_events"
)

SUBSCRIPTION_LIFECYCLE_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(SUBSCRIPTION_EVENTS, SubscriptionEventDocument),
)

SUBSCRIPTION_LIFECYCLE_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    SUBSCRIPTION_EVENTS: (text_field("kind"), integer_field("occurred_at")),
}
