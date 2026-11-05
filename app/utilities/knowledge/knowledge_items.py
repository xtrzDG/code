"""Build, replace and upsert knowledge items (the knowledge base and the wizard).

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
    KnowledgeItemUpsertInput,
)
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.utilities.knowledge.aliases.alias_rules import carry_aliases, check_aliases
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
from app.utilities.knowledge.search_text import fold_words

MAX_UPSERT_ITEMS: int = 500
BOOKING_FIELDS: tuple[str, ...] = (
    "buffer_minutes",
    "performer_resource_ids",
    "seasonal_rates",
)
LINEAGE_FIELDS: tuple[str, ...] = (
    "import_batch_id",
    "correction_of",
    "shared_key",
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
        buffer_minutes=check_buffer(kind, item_input.buffer_minutes),
        performer_resource_ids=check_performers_allowed(
            kind, item_input.performer_resource_ids
        ),
        seasonal_rates=check_seasonal_rates(kind, item_input.seasonal_rates),
        tags=unique_tags(item_input.tags),
        attributes=check_attributes(item_input.attributes),
        languages=unique_languages(item_input.languages),
        aliases=check_aliases(item_input.aliases, business.languages),
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
    """An item with every field replaced (id, source, creation, the
    `LINEAGE_FIELDS` and the unset `BOOKING_FIELDS` kept: the wizard
    re-saves offers without them; unset aliases carried as an edit of the
    title carries them)."""

    kept: dict[str, object] = {
        field: getattr(existing, field)
        for field in BOOKING_FIELDS
        if field not in item_input.model_fields_set
    }
    replacement: KnowledgeItemDocument = build_knowledge_item(
        business=business,
        template=template,
        item_input=item_input.model_copy(update=kept),
        source=existing.source,
        now=now,
    )
    carried: dict[str, object] = (
        {}
        if "aliases" in item_input.model_fields_set
        else {"aliases": carry_aliases(existing, item_input.title)}
    )
    return replacement.model_copy(
        update={
            "id": existing.id,
            "created_at": existing.created_at,
            "alias_request": existing.alias_request,
            **lineage_of(existing),
            **carried,
        }
    )


def lineage_of(existing: KnowledgeItemDocument) -> dict[str, object]:
    """
    Where an item came from, which no edit of its content changes: the
    import it is a draft of, the answer it corrects and the brand's shared
    answer it replaces in its location (an edited replacement still
    replaces the brand's answer).
    """

    return {field: getattr(existing, field) for field in LINEAGE_FIELDS}


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
