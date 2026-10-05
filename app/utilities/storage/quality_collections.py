"""
The catalog entries of production quality (1120): the judge's scores of
real conversations (a business collection) and their lookup fields. Part
of DOCUMENT_COLLECTIONS (document_collection_catalog.py) and
DOCUMENT_LOOKUP_FIELDS (document_lookup_catalog.py).
"""

from collections.abc import Mapping

from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field

QUALITY_SCORES: DocumentCollectionName = DocumentCollectionName(
    "conversation_quality_scores"
)
QUALITY_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(QUALITY_SCORES, ConversationQualityScoreDocument),
)
# A business's days and lowest scores and, across businesses, the night's
# spending, the QUALITY_DROP alert and the 90-day purge, by when the
# judge scored; the daily sums of scores and costs.
QUALITY_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    QUALITY_SCORES: (
        integer_field("judged_at"),
        integer_field("score_hundredths"),
        integer_field("cost_micro_usd"),
    ),
}
