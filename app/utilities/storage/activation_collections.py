"""
The collections of the activation follow-up (migration 1080), a part of the
collection catalog (`document_collection_catalog.py`):

- `nudges_sent`: each activation nudge a business was sent, once per
  business and nudge (the id derives from both);
- `onboarding_requests`: a business's request for a done-for-you setup.
"""

from app.schemas.domain.billing import OnboardingRequestDocument
from app.schemas.domain.setup import NudgeSentDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

NUDGES_SENT_COLLECTION: DocumentCollectionName = DocumentCollectionName("nudges_sent")
ONBOARDING_REQUESTS_COLLECTION: DocumentCollectionName = DocumentCollectionName(
    "onboarding_requests"
)
ACTIVATION_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(NUDGES_SENT_COLLECTION, NudgeSentDocument),
    DocumentCollectionDefinition(
        ONBOARDING_REQUESTS_COLLECTION, OnboardingRequestDocument
    ),
)
