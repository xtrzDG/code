"""
The partners' commissions (migration 1150): one per paid invoice, a
partner's newest first, and sums per currency and status that the
database computes (a partner's portal, a payout month).
"""

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.referral_repositories import (
    CommissionEntryRepoContract,
)
from app.repositories.document_queries import document_position, field_equals
from app.schemas.constants.referrals import CommissionStatus
from app.schemas.domain.referrals import CommissionEntryDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.referrals.commission_totals import CommissionTotal
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFilter
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.referrals.constrained_integers import CommissionInvoiceCount
from app.schemas.typings.referrals.constrained_strings import CommissionMonth
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

PARTNER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("partner_id")
MONTH_FIELD: DocumentFieldPath = DocumentFieldPath("month")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
CURRENCY_FIELD: DocumentFieldPath = DocumentFieldPath("currency_code")
ACCRUED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("accrued_at")
AMOUNT_FIELD: DocumentFieldPath = DocumentFieldPath("amount_minor")


class CommissionEntryRepository(CommissionEntryRepoContract):
    """Commissions keyed by id (derived from the invoice that earned them)."""

    def __init__(
        self, collection: DocumentCollectionAdapterContract[CommissionEntryDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            CommissionEntryDocument
        ] = collection

    def record(self, entry: CommissionEntryDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(entry.id), entry))

    def save(self, entry: CommissionEntryDocument) -> None:
        self._collection.upsert(str(entry.id), entry)

    def page_by_partner(
        self, partner_id: PartnerId, window: KeysetSlice
    ) -> list[CommissionEntryDocument]:
        return self._collection.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    matches=(field_equals(PARTNER_ID_FIELD, partner_id),)
                ),
                sort_fields=(ACCRUED_AT_FIELD,),
                after=document_position(window.after),
                limit=DocumentQueryLimit(int(window.limit)),
            )
        )

    def totals_by_partner(self, partner_id: PartnerId) -> list[CommissionTotal]:
        return [
            CommissionTotal(
                partner_id=partner_id,
                currency_code=CurrencyCode(str(group.values[0])),
                status=CommissionStatus(str(group.values[1])),
                invoice_count=CommissionInvoiceCount(int(group.count)),
                amount_minor=MoneyAmountMinor(int(group.totals[0])),
            )
            for group in self._sums(
                (field_equals(PARTNER_ID_FIELD, partner_id),),
                (CURRENCY_FIELD, STATUS_FIELD),
            )
        ]

    def totals_of_month(self, month: CommissionMonth) -> list[CommissionTotal]:
        return [
            CommissionTotal(
                partner_id=PartnerId(str(group.values[0])),
                currency_code=CurrencyCode(str(group.values[1])),
                status=CommissionStatus(str(group.values[2])),
                invoice_count=CommissionInvoiceCount(int(group.count)),
                amount_minor=MoneyAmountMinor(int(group.totals[0])),
            )
            for group in self._sums(
                (field_equals(MONTH_FIELD, month),),
                (PARTNER_ID_FIELD, CURRENCY_FIELD, STATUS_FIELD),
            )
        ]

    def list_of_month(
        self,
        partner_id: PartnerId,
        month: CommissionMonth,
        status: CommissionStatus,
    ) -> list[CommissionEntryDocument]:
        return self._collection.list_by_fields(
            (
                field_equals(MONTH_FIELD, month),
                field_equals(PARTNER_ID_FIELD, partner_id),
                field_equals(STATUS_FIELD, status),
            )
        )

    def _sums(
        self,
        matches: tuple[DocumentFieldMatch, ...],
        group_by: tuple[DocumentFieldPath, ...],
    ) -> list[DocumentGroupCount]:
        return [
            group
            for group in self._collection.count_by(
                DocumentAggregation(
                    where=DocumentFilter(matches=matches),
                    group_by=group_by,
                    totals_of=(AMOUNT_FIELD,),
                )
            )
            if all(value is not None for value in group.values)
        ]
