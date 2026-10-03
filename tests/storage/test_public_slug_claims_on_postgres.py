"""
Public chat addresses on Postgres: an address is unique across businesses
although row-level security hides one business's claims from another, and
a visitor's page finds any claim only when it looks platform-wide.
"""

from app.repositories.sharing_repositories import PublicSlugClaimRepository
from app.schemas.domain.public_slugs import PublicSlugClaimDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug
from app.use_cases.sharing.public_slug_claims import claim_slug
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory
from tests.storage.storage_testing import build_fixed_wall_clock

SLUG = BusinessPublicSlug("cafe-batumi")


def build_repository(
    collections: CollectionFactory,
) -> PublicSlugClaimRepository:
    return PublicSlugClaimRepository(
        collections(PublicSlugClaimDocument, "public_slug_claims")
    )


def test_two_businesses_never_share_an_address(
    collections: CollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    claims = build_repository(collections)
    first, second = BusinessId(), BusinessId()
    now = build_fixed_wall_clock().now_unix()

    with storage_scope.scoped_to_business(first):
        assert claim_slug(claims, first, SLUG, now) is True
        # Taking one's own address again succeeds and changes nothing.
        assert claim_slug(claims, first, SLUG, now) is True
    with storage_scope.scoped_to_business(second):
        # On Postgres the first business's claim is invisible here, and the
        # insert still sees the key taken.
        assert claim_slug(claims, second, SLUG, now) is False

    with storage_scope.platform_wide():
        found = claims.get(SLUG)
    assert found is not None
    assert found.business_id == first
