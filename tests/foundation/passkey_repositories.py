"""In-memory passkey repositories for tests that build use cases by hand."""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.passkey_repositories import (
    PasskeyChallengeRepository,
    PasskeyRepository,
)
from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument


def in_memory_passkey_repo() -> PasskeyRepository:
    return PasskeyRepository(
        InMemoryDocumentCollectionAdapter[PasskeyDocument](PasskeyDocument)
    )


def in_memory_passkey_challenge_repo() -> PasskeyChallengeRepository:
    return PasskeyChallengeRepository(
        InMemoryDocumentCollectionAdapter[PasskeyChallengeDocument](
            PasskeyChallengeDocument
        )
    )
