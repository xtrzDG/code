"""
Menu import (concept section 3): a photo, PDF or link is read by the model
into knowledge item drafts with a confidence score; the owner confirms each.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.dto.knowledge import KnowledgeItemView
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.knowledge.constrained_strings import KnowledgeTag
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.menu_import.booleans import IsCurrencyMismatch
from app.schemas.typings.menu_import.constrained_floats import ExtractionConfidence
from app.schemas.typings.menu_import.constrained_integers import MenuLineCount
from app.schemas.typings.menu_import.constrained_strings import (
    ExtractedPriceAmount,
    MenuSourceMediaType,
)
from app.schemas.typings.menu_import.strings import MenuSourceBase64
from app.schemas.typings.users.prefixed_id import UserId


class MenuImportRequest(ImmutableDTO):
    """
    HTTP body of a menu import: exactly one of an uploaded file
    (`data_base64` with its `media_type`: an image, a PDF or plain text) or
    a public `url` (then `media_type` is a hint and the served type wins).
    """

    media_type: MenuSourceMediaType
    data_base64: MenuSourceBase64 | None = None
    url: WebLink | None = None


class ImportMenuCommand(ImmutableDTO):
    """An owner or staff member imports a menu into the business knowledge base."""

    user_id: UserId
    business_id: BusinessId
    request: MenuImportRequest


class MenuExtractionRequest(ImmutableDTO):
    """
    What the extraction model reads. `language` is the business default
    language (titles stay as printed); `currency_code` is the business
    currency, used when the menu shows no currency.
    """

    media_type: MenuSourceMediaType
    data_base64: MenuSourceBase64 | None = None
    url: WebLink | None = None
    language: LanguageTag
    currency_code: CurrencyCode


class ExtractedMenuItem(ImmutableDTO):
    """One line read from a menu or price list."""

    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price: ExtractedPriceAmount | None = None
    currency_code: CurrencyCode | None = None
    duration_minutes: ServiceDurationMinutes | None = None
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])
    confidence: ExtractionConfidence


class MenuExtraction(ImmutableDTO):
    """Lines the model read; lines it returned in an unusable shape are counted."""

    items: list[ExtractedMenuItem] = Field(default_factory=list[ExtractedMenuItem])
    skipped_line_count: MenuLineCount = MenuLineCount(0)


class ImportedMenuItemView(ImmutableDTO):
    """
    An inactive knowledge item draft waiting for the owner's confirmation.

    When the menu shows another currency than the business currency the
    price is not converted (rates are never invented): `price_minor` stays
    empty, the printed price is kept and `is_currency_mismatch` is set.
    """

    item: KnowledgeItemView
    confidence: ExtractionConfidence
    is_currency_mismatch: IsCurrencyMismatch
    printed_price: ExtractedPriceAmount | None = None
    printed_currency_code: CurrencyCode | None = None


class MenuImportResult(ImmutableDTO):
    """Drafts created by one import, in menu order."""

    business_id: BusinessId
    items: list[ImportedMenuItemView] = Field(
        default_factory=list[ImportedMenuItemView]
    )
    skipped_line_count: MenuLineCount = MenuLineCount(0)


class ConfirmImportedItemsRequest(ImmutableDTO):
    """HTTP body: imported drafts the owner checked and wants the assistant to use."""

    item_ids: list[KnowledgeItemId]


class ConfirmImportedItemsCommand(ImmutableDTO):
    """Activate imported knowledge item drafts."""

    user_id: UserId
    business_id: BusinessId
    item_ids: list[KnowledgeItemId]


class ConfirmImportedItemsResult(ImmutableDTO):
    """Items now active in the knowledge base."""

    business_id: BusinessId
    activated_items: list[KnowledgeItemView] = Field(
        default_factory=list[KnowledgeItemView]
    )
