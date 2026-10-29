"""Taking public chat addresses for a business (helpers of the sharing use cases)."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.sharing_repositories import (
    PublicSlugClaimRepoContract,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.public_slugs import PublicSlugClaimDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug
from app.utilities.sharing.public_slugs import suggest_slugs


def claim_slug(
    claim_repo: PublicSlugClaimRepoContract,
    business_id: BusinessId,
    slug: BusinessPublicSlug,
    now: Microseconds,
) -> bool:
    """
    Take an address for the business (atomic): True when it is now the
    business's, also when the business took it before (its own old address
    comes back); False when another business has it.
    """

    is_claimed: bool = claim_repo.claim(
        PublicSlugClaimDocument(
            business_id=business_id,
            slug=slug,
            created_at=now,
            updated_at=now,
        )
    )
    if is_claimed:
        return True

    # Inside the business's storage scope only its own claims are visible.
    existing: PublicSlugClaimDocument | None = claim_repo.get(slug)
    return existing is not None and existing.business_id == business_id


def claim_first_free_slug(
    claim_repo: PublicSlugClaimRepoContract,
    business_id: BusinessId,
    candidates: Sequence[BusinessPublicSlug],
    now: Microseconds,
) -> BusinessPublicSlug | None:
    """The first candidate the business could take, or None."""

    for candidate in candidates:
        if claim_slug(claim_repo, business_id, candidate, now):
            return candidate

    return None


def ensure_public_slug(
    business_repo: BusinessRepoContract,
    claim_repo: PublicSlugClaimRepoContract,
    business: BusinessDocument,
    now: Microseconds,
) -> tuple[BusinessDocument, BusinessPublicSlug]:
    """
    The business and its public chat address: its own, or, the first time
    it shares the assistant, one suggested from its name (taken atomically
    and stored only while it still has none, so two first visits agree).
    """

    if business.public_slug is not None:
        return business, business.public_slug

    slug: BusinessPublicSlug | None = claim_first_free_slug(
        claim_repo, business.id, suggest_slugs(business.name, business.id), now
    )
    if slug is None:
        # Every suggestion is taken, even the one made from the id.
        raise RuntimeError(f"No free public address for business {business.id}.")

    def set_first_slug(stored: BusinessDocument) -> None:
        if stored.public_slug is None:
            stored.public_slug = slug

    updated: BusinessDocument = business_repo.update(business.id, set_first_slug)
    # Another first visit may have stored its own suggestion meanwhile.
    return updated, updated.public_slug or slug
