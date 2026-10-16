"""
The catalog entries of the spend guard (1142): each business's limits (its
daily spend ceilings and the websites allowed to show its chat) and the
marks of the days it passed one of its spend limits. Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py) and of the lookup
catalog (document_lookup_catalog.py).
"""

from collections.abc import Mapping

from app.schemas.domain.business_limits import (
    BusinessLimitsDocument,
    SpendLimitMarkDocument,
)
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import text_field

SPEND_GUARD_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("business_limits"), BusinessLimitsDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("spend_limit_marks"), SpendLimitMarkDocument
    ),
)
# The marks of one day across businesses: the admin's spend tile names the
# businesses that passed a limit today.
SPEND_GUARD_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    DocumentCollectionName("spend_limit_marks"): (text_field("day"),),
}
