"""Build, change and upsert knowledge items (the knowledge base and the wizard).

Each value is checked by `knowledge_item_checks`; the views the model and
the owner see are in `knowledge_item_views`.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemInput,
    KnowledgeItemPatch,
    KnowledgeItemUpsertInput,
)
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.profiles.business_profile import FaqEntryInput
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.strings import KnowledgeTitle
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
from app.utilities.knowledge.search_text import fold_words

MAX_UPSERT_ITEMS: int = 500
REQUIRED_PATCH_FIELDS: tuple[str, ...] = (
    "kind",
    "title",
    "tags",
    "attributes",
    "languages",
    "is_active",
)


def build_knowledge_item(
    business: BusinessDocument,
    template: NicheTemplate,
    item_input: KnowledgeItemInput,
    source: KnowledgeItemSource,
    now: Microseconds,
) -> KnowledgeItemDocument:
    """A validated new knowledge item of the business."""

    kind: KnowledgeItemKind = check_kind(template, item_input.kind)
    price_minor, currency_code = check_price(
        business,
        item_input.price_minor,
        item_input.currency_code,
    )
    return KnowledgeItemDocument(
        business_id=business.id,
        kind=kind,
        title=check_title(item_input.title),
        body=check_body(item_input.body),
        price_minor=price_minor,
        currency_code=currency_code,
        duration_minutes=item_input.duration_minutes,
        tags=unique_tags(item_input.tags),
        attributes=check_attributes(item_input.attributes),
        languages=unique_languages(item_input.languages),
        source=source,
        is_active=item_input.is_active,
        created_at=now,
        updated_at=now,
    )


def replace_knowledge_item(
    business: BusinessDocument,
    template: NicheTemplate,
    existing: KnowledgeItemDocument,
    item_input: KnowledgeItemInput,
    now: Microseconds,
) -> KnowledgeItemDocument:
    """An existing item with all fields replaced; id, source and creation kept."""

    replacement: KnowledgeItemDocument = build_knowledge_item(
        business=business,
        template=template,
        item_input=item_input,
        source=existing.source,
        now=now,
    )
    return replacement.model_copy(
        update={"id": existing.id, "created_at": existing.created_at}
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
    unless the patch changes the price or the currency.
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

    return KnowledgeItemDocument(
        id=existing.id,
        business_id=existing.business_id,
        kind=existing.kind if patch.kind is None else check_kind(template, patch.kind),
        title=existing.title if patch.title is None else check_title(patch.title),
        body=check_body(patch.body) if "body" in provided else existing.body,
        price_minor=price_minor,
        currency_code=currency_code,
        duration_minutes=(
            patch.duration_minutes
            if "duration_minutes" in provided
            else existing.duration_minutes
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
        created_at=existing.created_at,
        updated_at=now,
    )


def upsert_knowledge_items(
    business: BusinessDocument,
    template: NicheTemplate,
    existing_items: Sequence[KnowledgeItemDocument],
    item_inputs: Sequence[KnowledgeItemUpsertInput],
    source: KnowledgeItemSource,
    now: Microseconds,
) -> list[KnowledgeItemDocument]:
    """
    Validated items to save: updates of existing items and new ones.

    An input with an id replaces that item of the business; without an id it
    replaces the item of the same kind and title, or creates a new item. The
    whole batch is validated before anything is returned, so a bad item
    leaves the knowledge base unchanged.

    Raises:
        NotFoundError: an id does not belong to this business.
        ValidationFailedError: an item breaks a knowledge rule.
    """

    if len(item_inputs) > MAX_UPSERT_ITEMS:
        raise ValidationFailedError(
            f"At most {MAX_UPSERT_ITEMS} items can be saved at once."
        )

    working_items: dict[str, KnowledgeItemDocument] = {
        str(item.id): item for item in existing_items
    }
    saved_ids: list[str] = []
    for item_input in item_inputs:
        target: KnowledgeItemDocument | None
        if item_input.id is not None:
            target = working_items.get(str(item_input.id))
            if target is None:
                raise NotFoundError(f"Knowledge item {item_input.id} was not found.")
        else:
            target = find_matching_item(
                list(working_items.values()),
                item_input.kind,
                item_input.title,
            )

        saved: KnowledgeItemDocument = (
            build_knowledge_item(
                business=business,
                template=template,
                item_input=item_input,
                source=source,
                now=now,
            )
            if target is None
            else replace_knowledge_item(
                business=business,
                template=template,
                existing=target,
                item_input=item_input,
                now=now,
            )
        )
        working_items[str(saved.id)] = saved
        if str(saved.id) not in saved_ids:
            saved_ids.append(str(saved.id))

    return [working_items[saved_id] for saved_id in saved_ids]


def faq_entry_to_upsert_input(entry: FaqEntryInput) -> KnowledgeItemUpsertInput:
    """A frequent question as a FAQ knowledge item (question as the title)."""

    return KnowledgeItemUpsertInput(
        id=entry.id,
        kind=KnowledgeItemKind.FAQ,
        title=entry.question,
        body=entry.answer,
        languages=list(entry.languages),
    )


def find_matching_item(
    items: Sequence[KnowledgeItemDocument],
    kind: KnowledgeItemKind,
    title: KnowledgeTitle,
) -> KnowledgeItemDocument | None:
    """The item of the same kind and title, ignoring case, accents and spacing."""

    folded_title: str = fold_words(title)
    for item in items:
        if item.kind is kind and fold_words(item.title) == folded_title:
            return item

    return None
