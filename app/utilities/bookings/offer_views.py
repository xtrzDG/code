"""Bookable offers as the model tools and the cabinet list them."""

from collections.abc import Sequence

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookable_offers import BookableOfferView, OfferPerformer
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.bookings.bookable_offers import (
    bookable_offers,
    buffer_of_offer,
    performers_of,
)

# The availability result lists at most this many offers to the model.
MAX_LISTED_OFFERS: int = 30


def build_offer_view(
    offer: KnowledgeItemDocument,
    resources: Sequence[ResourceDocument],
    items: Sequence[KnowledgeItemDocument],
    business_currency_code: CurrencyCode,
) -> BookableOfferView:
    return BookableOfferView(
        id=offer.id,
        kind=offer.kind,
        title=offer.title,
        duration_minutes=offer.duration_minutes,
        buffer_minutes=buffer_of_offer(offer),
        price_minor=offer.price_minor,
        currency_code=(
            None
            if offer.price_minor is None
            else offer.currency_code or business_currency_code
        ),
        performers=[
            OfferPerformer(resource_id=resource.id, resource_name=resource.name)
            for resource in sorted(
                performers_of(offer, resources, items),
                key=lambda resource: str(resource.name).casefold(),
            )
        ],
    )


def list_offer_views(
    resources: Sequence[ResourceDocument],
    items: Sequence[KnowledgeItemDocument],
    business_currency_code: CurrencyCode,
) -> list[BookableOfferView]:
    """The business's bookable offers with their performers, by kind and title."""

    return [
        build_offer_view(offer, resources, items, business_currency_code)
        for offer in bookable_offers(items)[:MAX_LISTED_OFFERS]
    ]
