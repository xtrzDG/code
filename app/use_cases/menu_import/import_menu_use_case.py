from decimal import Decimal

from typed_time_provider import Microseconds, WallClock

from app.contracts.brain import MenuExtractionAdapterContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeAttribute, KnowledgeItemDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.menu_import import (
    ExtractedMenuItem,
    ImportMenuCommand,
    MenuExtraction,
    MenuExtractionRequest,
    MenuImportRequest,
    MenuImportResult,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.strings import KnowledgeAttributeValue
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.use_cases.menu_import.imported_item_views import (
    CONFIDENCE_ATTRIBUTE,
    PRINTED_CURRENCY_ATTRIBUTE,
    PRINTED_PRICE_ATTRIBUTE,
    build_imported_item_view,
)
from app.utilities.money.money_math import build_money_from_major_units

UPLOAD_MEDIA_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "application/pdf",
        "text/plain",
        "text/csv",
        "text/html",
    }
)


class ImportMenuUseCase(UseCaseContract[ImportMenuCommand, MenuImportResult]):
    """
    Read a menu or price list from a photo, PDF, text or link (concept
    section 3) into knowledge item drafts.

    Drafts are inactive (the assistant does not use them) until the owner
    confirms them, carry the model's confidence and the id of this import
    (to discard the rest at once), and come from MENU_IMPORT.
    Prices become minor units of the business currency; a line printed in
    another currency keeps its printed price and is flagged instead, because
    exchange rates are never invented.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        menu_extraction_adapter: MenuExtractionAdapterContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._menu_extraction_adapter: MenuExtractionAdapterContract = (
            menu_extraction_adapter
        )
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ImportMenuCommand) -> MenuImportResult:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        validate_import_request(input_data.request)
        extraction: MenuExtraction = self._menu_extraction_adapter.extract(
            MenuExtractionRequest(
                media_type=input_data.request.media_type,
                data_base64=input_data.request.data_base64,
                url=input_data.request.url,
                language=business.default_language,
                currency_code=business.currency_code,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        batch_id: MenuImportBatchId = MenuImportBatchId()
        drafts: list[KnowledgeItemDocument] = [
            build_draft(business, extracted_item, batch_id, now)
            for extracted_item in extraction.items
        ]
        for draft in drafts:
            self._knowledge_item_repo.save(draft)

        return MenuImportResult(
            business_id=business.id,
            batch_id=batch_id,
            items=[
                build_imported_item_view(draft, business.owner_language)
                for draft in drafts
            ],
            skipped_line_count=extraction.skipped_line_count,
        )


def validate_import_request(request: MenuImportRequest) -> None:
    has_file: bool = request.data_base64 is not None
    has_link: bool = request.url is not None
    if has_file == has_link:
        raise ValidationFailedError(
            "Send either a menu file (data_base64) or a link (url), not both."
        )

    if not has_file:
        return

    if str(request.media_type) not in UPLOAD_MEDIA_TYPES:
        raise ValidationFailedError(
            "A menu file must be a JPEG, PNG, WebP or GIF photo, a PDF or text."
        )


def build_draft(
    business: BusinessDocument,
    extracted_item: ExtractedMenuItem,
    batch_id: MenuImportBatchId,
    now: Microseconds,
) -> KnowledgeItemDocument:
    printed_currency: CurrencyCode = (
        extracted_item.currency_code
        if extracted_item.currency_code is not None
        else business.currency_code
    )
    is_currency_mismatch: bool = (
        extracted_item.price is not None and printed_currency != business.currency_code
    )
    attributes: list[KnowledgeAttribute] = [
        KnowledgeAttribute(
            key=CONFIDENCE_ATTRIBUTE,
            value=KnowledgeAttributeValue(f"{float(extracted_item.confidence):.2f}"),
        )
    ]
    price_minor: MoneyAmountMinor | None = None
    if extracted_item.price is not None and not is_currency_mismatch:
        price_minor = build_money_from_major_units(
            Decimal(str(extracted_item.price)),
            business.currency_code,
        ).amount_minor
    elif extracted_item.price is not None:
        attributes.extend(
            [
                KnowledgeAttribute(
                    key=PRINTED_PRICE_ATTRIBUTE,
                    value=KnowledgeAttributeValue(str(extracted_item.price)),
                ),
                KnowledgeAttribute(
                    key=PRINTED_CURRENCY_ATTRIBUTE,
                    value=KnowledgeAttributeValue(str(printed_currency)),
                ),
            ]
        )

    return KnowledgeItemDocument(
        business_id=business.id,
        kind=extracted_item.kind,
        title=extracted_item.title,
        body=extracted_item.body,
        price_minor=price_minor,
        currency_code=None if price_minor is None else business.currency_code,
        duration_minutes=extracted_item.duration_minutes,
        tags=list(extracted_item.tags),
        attributes=attributes,
        source=KnowledgeItemSource.MENU_IMPORT,
        is_active=False,
        import_batch_id=batch_id,
        created_at=now,
        updated_at=now,
    )
