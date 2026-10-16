"""Change the fields of a knowledge item an owner's patch names (the
knowledge base editor); building and replacing items is in
`knowledge_items`."""

from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import KnowledgeItemPatch
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.knowledge.knowledge_item_checks import (
    check_attributes,
    check_body,
    check_kind,
    check_price,
    check_title,
    unique_languages,
    unique_tags,
)
from app.utilities.knowledge.offer_checks import (
    check_buffer,
    check_performers_allowed,
    check_seasonal_rates,
)

REQUIRED_PATCH_FIELDS: tuple[str, ...] = (
    "kind",
    "title",
    "tags",
    "attributes",
    "languages",
    "is_active",
)


def patch_knowledge_item(
    business: BusinessDocument,
    template: NicheTemplate,
    existing: KnowledgeItemDocument,
    patch: KnowledgeItemPatch,
    now: Microseconds,
) -> KnowledgeItemDocument:
    """
    An existing item with the fields present in `patch` changed.

    A field explicitly set to null clears it; required fields (kind, title,
    lists, active flag) cannot be cleared. A stored price is kept untouched
    unless the patch changes the price or the currency. Where the item
    came from (`lineage_of`) stays as it was.
    """

    provided: set[str] = patch.model_fields_set
    for required_field in REQUIRED_PATCH_FIELDS:
        if required_field in provided and getattr(patch, required_field) is None:
            raise ValidationFailedError(f"Field {required_field} cannot be null.")

    price_minor: MoneyAmountMinor | None = existing.price_minor
    currency_code: CurrencyCode | None = existing.currency_code
    if "price_minor" in provided or "currency_code" in provided:
        price_minor, currency_code = check_price(
            business,
            patch.price_minor if "price_minor" in provided else existing.price_minor,
            patch.currency_code,
        )

    kind: KnowledgeItemKind = (
        existing.kind if patch.kind is None else check_kind(template, patch.kind)
    )
    return KnowledgeItemDocument(
        id=existing.id,
        business_id=existing.business_id,
        kind=kind,
        title=existing.title if patch.title is None else check_title(patch.title),
        body=check_body(patch.body) if "body" in provided else existing.body,
        price_minor=price_minor,
        currency_code=currency_code,
        duration_minutes=(
            patch.duration_minutes
            if "duration_minutes" in provided
            else existing.duration_minutes
        ),
        buffer_minutes=check_buffer(
            kind,
            (
                patch.buffer_minutes
                if "buffer_minutes" in provided
                else existing.buffer_minutes
            ),
        ),
        performer_resource_ids=check_performers_allowed(
            kind,
            (
                existing.performer_resource_ids
                if patch.performer_resource_ids is None
                else patch.performer_resource_ids
            ),
        ),
        seasonal_rates=check_seasonal_rates(
            kind,
            (
                existing.seasonal_rates
                if patch.seasonal_rates is None
                else patch.seasonal_rates
            ),
        ),
        tags=existing.tags if patch.tags is None else unique_tags(patch.tags),
        attributes=(
            existing.attributes
            if patch.attributes is None
            else check_attributes(patch.attributes)
        ),
        languages=(
            existing.languages
            if patch.languages is None
            else unique_languages(patch.languages)
        ),
        source=existing.source,
        is_active=existing.is_active if patch.is_active is None else patch.is_active,
        import_batch_id=existing.import_batch_id,
        correction_of=existing.correction_of,
        shared_key=existing.shared_key,
        created_at=existing.created_at,
        updated_at=now,
    )
