from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field

from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.booleans import IsKnowledgeItemActive
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.knowledge.constrained_strings import (
    KnowledgeAttributeKey,
    KnowledgeTag,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import (
    KnowledgeAttributeValue,
    KnowledgeBody,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)


class KnowledgeAttribute(PersistentDocument):
    """Structured attribute of a knowledge item ("season": "summer")."""

    key: KnowledgeAttributeKey
    value: KnowledgeAttributeValue


class KnowledgeItemDocument(BaseDocument):
    """
    One fact the assistant may use (concept table `knowledge_items`).

    Prices are integers in minor units of the business currency, so the
    assistant can name a price only if it is stored here.
    """

    id: KnowledgeItemId = Field(default_factory=KnowledgeItemId)
    business_id: BusinessId
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    duration_minutes: ServiceDurationMinutes | None = None
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])
    attributes: list[KnowledgeAttribute] = Field(
        default_factory=list[KnowledgeAttribute]
    )
    languages: list[LanguageTag] = Field(default_factory=list[LanguageTag])
    source: KnowledgeItemSource = KnowledgeItemSource.OWNER
    is_active: IsKnowledgeItemActive = True
