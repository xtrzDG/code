from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.accounts.prefixed_id import OwnerId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class BusinessAccessRequest(ImmutableDTO):
    """Check that an authenticated owner may act on a business."""

    owner_id: OwnerId
    business_id: BusinessId
