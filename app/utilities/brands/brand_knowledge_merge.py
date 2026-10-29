"""
The knowledge a location's assistant answers from: its own items and the
facts its brand shares, merged at assembly (and by the knowledge tools),
never stored in the location.

Override order: a location item carrying a shared fact's key replaces the
fact in that location (an active one with its own content, an inactive
one hides it); every other active shared fact is added. A shared price
in another currency than the location's is left out, so the assistant
never names a price in a currency the location does not take.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.domain.brands import BrandKnowledgeItemDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId


def merge_brand_knowledge(
    location_items: list[KnowledgeItemDocument],
    shared_items: list[BrandKnowledgeItemDocument],
    business: BusinessDocument,
) -> list[KnowledgeItemDocument]:
    """The location's items as they are, then the shared facts it keeps."""

    return [
        *location_items,
        *(
            as_location_item(shared, business)
            for shared in unreplaced_shared_items(location_items, shared_items)
            if shared.is_active
        ),
    ]


def knowledge_revisions(
    location_items: list[KnowledgeItemDocument],
    shared_items: list[BrandKnowledgeItemDocument],
    business: BusinessDocument,
) -> list[KnowledgeItemDocument]:
    """
    Every item whose change reaches the location's assistant, active or
    not, each with when it last changed: the location's own items and the
    shared facts it does not replace (a fact the brand turned off counts:
    the assistant must stop saying it). For "is the version up to date".
    """

    return [
        *location_items,
        *(
            as_location_item(shared, business)
            for shared in unreplaced_shared_items(location_items, shared_items)
        ),
    ]


def unreplaced_shared_items(
    location_items: list[KnowledgeItemDocument],
    shared_items: list[BrandKnowledgeItemDocument],
) -> list[BrandKnowledgeItemDocument]:
    """The shared facts no location item replaces (by the fact's key)."""

    replaced: set[KnowledgeShareKey] = {
        item.shared_key for item in location_items if item.shared_key is not None
    }
    return [shared for shared in shared_items if shared.shared_key not in replaced]


def as_location_item(
    shared: BrandKnowledgeItemDocument,
    business: BusinessDocument,
) -> KnowledgeItemDocument:
    """A shared fact read as one of the location's items (same id, never stored)."""

    return build_location_item(
        shared, business, shared.id, shared.updated_at
    ).model_copy(update={"is_active": shared.is_active})


def location_copy(
    shared: BrandKnowledgeItemDocument,
    business: BusinessDocument,
    now: Microseconds,
) -> KnowledgeItemDocument:
    """A new item of the location that replaces the shared fact there."""

    return build_location_item(shared, business, KnowledgeItemId(), now)


def build_location_item(
    shared: BrandKnowledgeItemDocument,
    business: BusinessDocument,
    item_id: KnowledgeItemId,
    written_at: Microseconds,
) -> KnowledgeItemDocument:
    is_priced_here: bool = (
        shared.price_minor is not None
        and shared.currency_code == business.currency_code
    )
    return KnowledgeItemDocument(
        id=item_id,
        business_id=business.id,
        kind=shared.kind,
        title=shared.title,
        body=shared.body,
        price_minor=shared.price_minor if is_priced_here else None,
        currency_code=shared.currency_code if is_priced_here else None,
        tags=list(shared.tags),
        languages=list(shared.languages),
        source=KnowledgeItemSource.OWNER,
        is_active=True,
        shared_key=shared.shared_key,
        created_at=written_at,
        updated_at=written_at,
    )
