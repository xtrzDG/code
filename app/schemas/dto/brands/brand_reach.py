from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessDocument


class BusinessReach(ImmutableDTO):
    """
    A business a person works in and the role they act with there: their
    own membership, or the one their brand gives them (a brand owner owns
    every location, a regional manager is staff of the assigned ones).
    `brand` is the business's brand when the person is on that brand's
    team (the cabinet groups its locations under it), else None.
    """

    business: BusinessDocument
    role: BusinessMemberRole
    brand: BrandDocument | None = None
