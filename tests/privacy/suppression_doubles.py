"""The real suppression list over an in-memory collection, for tests."""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.privacy.suppression_list_facilitator import (
    SuppressionListFacilitator,
)
from app.repositories.privacy_repositories import SuppressionEntryRepository
from app.schemas.domain.suppression import SuppressionEntryDocument
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.privacy.suppression_digests import derive_suppression_key

TEST_SUPPRESSION_KEY: PlatformSecret = PlatformSecret("test-suppression-key-0000")


def build_suppression_list(
    repo: SuppressionEntryRepository | None = None,
) -> SuppressionListFacilitator:
    """A suppression list with its own in-memory entries (or `repo`'s)."""

    return SuppressionListFacilitator(
        suppression_entry_repo=repo
        or SuppressionEntryRepository(
            InMemoryDocumentCollectionAdapter(SuppressionEntryDocument)
        ),
        suppression_key=derive_suppression_key(TEST_SUPPRESSION_KEY, None),
    )
