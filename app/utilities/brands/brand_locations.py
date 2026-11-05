"""
A brand's first location: the oldest business in it (the one written
first, ties broken by id). It pays the plan price and is shown first;
every further location pays the plan's additional-location price.
"""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.brands.booleans import IsAdditionalLocation
from app.schemas.typings.businesses.prefixed_id import BusinessId


def oldest_first(locations: list[BusinessDocument]) -> list[BusinessDocument]:
    return sorted(locations, key=lambda item: (int(item.created_at), str(item.id)))


def first_location_id(locations: list[BusinessDocument]) -> BusinessId | None:
    ordered: list[BusinessDocument] = oldest_first(locations)
    return ordered[0].id if ordered else None


def is_further_location(
    business: BusinessDocument, locations: list[BusinessDocument]
) -> IsAdditionalLocation:
    """
    Whether the business is a brand location other than the first one. A
    business outside any brand, or alone in its brand, is not.
    """

    if business.brand_id is None:
        return False

    in_brand: list[BusinessDocument] = [
        location
        for location in locations
        if location.brand_id == business.brand_id or location.id == business.id
    ]
    first: BusinessId | None = first_location_id(in_brand)
    return first is not None and first != business.id
