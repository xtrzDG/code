from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.sharing_repositories import (
    PublicSlugClaimRepoContract,
)
from app.schemas.domain.public_slugs import PublicSlugClaimDocument
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug


class PublicSlugClaimRepository(PublicSlugClaimRepoContract):
    """
    Public chat addresses keyed by the slug itself: the storage key makes
    an address unique across businesses, and a claim is read by its key
    only. Row-level security shows a business only its own claims; the
    visitor's lookup of an address escalates to platform-wide itself.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PublicSlugClaimDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[PublicSlugClaimDocument] = (
            collection
        )

    def claim(self, claim: PublicSlugClaimDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(claim.slug), claim))

    def get(self, slug: BusinessPublicSlug) -> PublicSlugClaimDocument | None:
        return self._collection.get(str(slug))
