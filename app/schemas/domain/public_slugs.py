from base_pydantic_schemas import BaseDocument

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug


class PublicSlugClaimDocument(BaseDocument):
    """
    A public chat address (`/c/{slug}`) a business took, stored under the
    slug itself, so two businesses can never take one (the storage key is
    unique across businesses, also between concurrent requests).

    A claim outlives a change of address: the business keeps every slug it
    ever had, so printed QR codes and table cards still lead to it and no
    other business can take them over. The business's current address is
    `BusinessDocument.public_slug`. A visitor's page finds the claim of an
    address before the business is known: that one read looks across
    businesses explicitly (`StorageScopeContract.platform_wide`).
    """

    business_id: BusinessId
    slug: BusinessPublicSlug
