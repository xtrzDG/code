from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field

from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.booleans import IsKnowledgeItemActive
from app.schemas.typings.knowledge.constrained_integers import (
    BufferMinutes,
    NightlyRateMinor,
    ServiceDurationMinutes,
)
from app.schemas.typings.knowledge.constrained_strings import (
    KnowledgeAttributeKey,
    KnowledgeTag,
    SeasonDay,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import (
    KnowledgeAttributeValue,
    KnowledgeBody,
    KnowledgeTitle,
    SeasonName,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId


class KnowledgeAttribute(PersistentDocument):
    """Structured attribute of a knowledge item ("season": "summer")."""

    key: KnowledgeAttributeKey
    value: KnowledgeAttributeValue


class SeasonalNightlyRate(PersistentDocument):
    """
    The nightly rate of a room type from `starts_on` to `ends_on` (both
    included, every year; a season may run over New Year, "12-20" to
    "01-10"). Nights outside every season cost the item's `price_minor`.
    """

    starts_on: SeasonDay
    ends_on: SeasonDay
    nightly_rate_minor: NightlyRateMinor
    name: SeasonName | None = None


class KnowledgeItemDocument(BaseDocument):
    """
    One fact the assistant may use (concept table `knowledge_items`).

    Prices are integers in minor units of the business currency, so the
    assistant can name a price only if it is stored here. A menu import
    draft carries the `import_batch_id` of its import until the owner
    confirms it, so a whole import can be discarded at once.

    Bookable offers (services, packages, room types) say what a booking of
    them takes: `duration_minutes` plus `buffer_minutes` the performer
    stays blocked after it, the resources that perform or provide it
    (`performer_resource_ids`, together with the resources that list the
    item in their `serves_item_ids` or as their `room_type_item_id`), and
    for room types the `seasonal_rates` of a night (`price_minor` is the
    nightly rate outside every season).
    """

    # 2: `buffer_minutes`, `performer_resource_ids` and `seasonal_rates`
    # (optional); `duration_minutes` is 5 to 720 minutes, longer or shorter
    # ones of version 1 move to an attribute (upcaster).
    schema_version: SchemaVersion = SchemaVersion("2")
    id: KnowledgeItemId = Field(default_factory=KnowledgeItemId)
    business_id: BusinessId
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    duration_minutes: ServiceDurationMinutes | None = None
    buffer_minutes: BufferMinutes | None = None
    performer_resource_ids: list[ResourceId] = Field(default_factory=list[ResourceId])
    seasonal_rates: list[SeasonalNightlyRate] = Field(
        default_factory=list[SeasonalNightlyRate]
    )
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])
    attributes: list[KnowledgeAttribute] = Field(
        default_factory=list[KnowledgeAttribute]
    )
    languages: list[LanguageTag] = Field(default_factory=list[LanguageTag])
    source: KnowledgeItemSource = KnowledgeItemSource.OWNER
    is_active: IsKnowledgeItemActive = True
    import_batch_id: MenuImportBatchId | None = None
