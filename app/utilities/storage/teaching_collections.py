"""
The catalog entries of teaching the assistant (1112): the owner's own
checks ("My checks"), which every autotest run of the business plays
(a business collection). Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py).
"""

from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

TEACHING_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("autotest_cases"), AutotestCaseDocument
    ),
)
