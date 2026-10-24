"""
The catalog entries of passkeys (1201): part of DOCUMENT_COLLECTIONS
(through the sign-in collections) and DOCUMENT_LOOKUP_FIELDS (through the
platform's lookup fields). Platform collections: no business.

- passkeys: a person's passkeys, each stored under an id derived from its
  credential id (one credential is one passkey); a person's list by
  `user_id`;
- passkey_challenges: the challenge of one ceremony (five minutes), read
  by id, purged by age (`created_at`).
"""

from collections.abc import Mapping

from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field, text_field

PASSKEYS: DocumentCollectionName = DocumentCollectionName("passkeys")
PASSKEY_CHALLENGES: DocumentCollectionName = DocumentCollectionName(
    "passkey_challenges"
)

PASSKEY_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(PASSKEYS, PasskeyDocument),
    DocumentCollectionDefinition(PASSKEY_CHALLENGES, PasskeyChallengeDocument),
)

PASSKEY_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    PASSKEYS: (text_field("user_id"),),
    PASSKEY_CHALLENGES: (integer_field("created_at"),),
}
