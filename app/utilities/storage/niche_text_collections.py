"""
The catalog entries of the niche template editor (1221): part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py) and, through the
platform's lookup fields, DOCUMENT_LOOKUP_FIELDS. Platform collections:
they name no business.

- niche_text_drafts: the draft of a niche, stored under the niche's key
  (one per niche, read by key);
- niche_text_releases: every published version, stored under an id derived
  from the niche and the version; the newest of each niche is one indexed
  probe of (niche_key, version), a niche's history the same index.
"""

from collections.abc import Mapping

from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextReleaseDocument,
)
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field, text_field

NICHE_TEXT_DRAFTS: DocumentCollectionName = DocumentCollectionName("niche_text_drafts")
NICHE_TEXT_RELEASES: DocumentCollectionName = DocumentCollectionName(
    "niche_text_releases"
)

NICHE_TEXT_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(NICHE_TEXT_DRAFTS, NicheTextDraftDocument),
    DocumentCollectionDefinition(NICHE_TEXT_RELEASES, NicheTextReleaseDocument),
)

NICHE_TEXT_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    NICHE_TEXT_RELEASES: (text_field("niche_key"), integer_field("version")),
}
