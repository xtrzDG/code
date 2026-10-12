"""What a brand's shared fact may hold, shared by the brand knowledge use cases."""

import secrets

from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.brands import BrandKnowledgeItemDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.brands.brand_knowledge import (
    BrandKnowledgeItemRequest,
    BrandKnowledgeItemView,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.knowledge.knowledge_item_checks import (
    check_body,
    check_title,
    unique_languages,
    unique_tags,
)

# Facts the same in every location; offers that book a resource (services,
# room types, packages, vehicles) belong to each location.
BRAND_KNOWLEDGE_KINDS: frozenset[KnowledgeItemKind] = frozenset(
    {
        KnowledgeItemKind.FAQ,
        KnowledgeItemKind.POLICY,
        KnowledgeItemKind.MENU_ITEM,
        KnowledgeItemKind.PRODUCT,
    }
)
SHARE_KEY_SUFFIX_BYTES: int = 4


def new_share_key(kind: KnowledgeItemKind) -> KnowledgeShareKey:
    """A fresh key for a shared fact of this kind ("faq-3f9a2c1e")."""

    prefix: str = kind.value.replace("_", "-")
    return KnowledgeShareKey(f"{prefix}-{secrets.token_hex(SHARE_KEY_SUFFIX_BYTES)}")


def brand_currency(
    price_minor: MoneyAmountMinor | None,
    locations: list[BusinessDocument],
) -> CurrencyCode | None:
    """
    The currency of a shared price: the one every location keeps.

    Raises:
        ValidationFailedError: a price while the locations keep none or
            several currencies.
    """

    if price_minor is None:
        return None

    currencies: set[CurrencyCode] = {location.currency_code for location in locations}
    if len(currencies) != 1:
        raise ValidationFailedError(
            "A shared price needs every location of the brand in one currency; "
            "give each location its own price instead."
        )

    return next(iter(currencies))


def check_request(request: BrandKnowledgeItemRequest) -> None:
    """
    Raises:
        ValidationFailedError: a kind that belongs to each location, or a
            blank or overly long title or text.
    """

    if request.kind not in BRAND_KNOWLEDGE_KINDS:
        raise ValidationFailedError(
            "A brand shares FAQs, rules, menu items and products; services, "
            "rooms and packages belong to each location."
        )

    check_title(request.title)
    check_body(request.body)


def build_item(
    brand_id: BrandId,
    request: BrandKnowledgeItemRequest,
    currency_code: CurrencyCode | None,
    now: Microseconds,
) -> BrandKnowledgeItemDocument:
    return BrandKnowledgeItemDocument(
        brand_id=brand_id,
        shared_key=request.shared_key or new_share_key(request.kind),
        kind=request.kind,
        title=request.title,
        body=check_body(request.body),
        price_minor=request.price_minor,
        currency_code=currency_code,
        tags=unique_tags(request.tags),
        languages=unique_languages(request.languages),
        is_active=request.is_active,
        created_at=now,
        updated_at=now,
    )


def describe_item(
    item: BrandKnowledgeItemDocument,
    overridden_in: list[BusinessId],
) -> BrandKnowledgeItemView:
    return BrandKnowledgeItemView(
        id=item.id,
        shared_key=item.shared_key,
        kind=item.kind,
        title=item.title,
        body=item.body,
        price_minor=item.price_minor,
        currency_code=item.currency_code,
        tags=list(item.tags),
        languages=list(item.languages),
        is_active=item.is_active,
        overridden_in=overridden_in,
        updated_at=item.updated_at,
    )
