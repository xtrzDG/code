"""
The catalog entries of brands, chains of locations run by one team (1192),
both platform collections: the brands (a person's brands by the members'
user ids) and the facts a brand's locations share (a brand's items, keyed
by brand and shared key). Which businesses a brand has is the `brand_id`
lookup column of `businesses` (document_lookup_catalog.py). Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py) and
DOCUMENT_LOOKUP_FIELDS (document_lookup_catalog.py).
"""

from collections.abc import Mapping

from app.schemas.domain.brands import BrandDocument, BrandKnowledgeItemDocument
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import element_field, text_field

BRANDS: DocumentCollectionName = DocumentCollectionName("brands")
BRAND_KNOWLEDGE_ITEMS: DocumentCollectionName = DocumentCollectionName(
    "brand_knowledge_items"
)

BRAND_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(BRANDS, BrandDocument),
    DocumentCollectionDefinition(BRAND_KNOWLEDGE_ITEMS, BrandKnowledgeItemDocument),
)

BRAND_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    BRANDS: (element_field("members[].user_id"),),
    BRAND_KNOWLEDGE_ITEMS: (text_field("brand_id"),),
}
