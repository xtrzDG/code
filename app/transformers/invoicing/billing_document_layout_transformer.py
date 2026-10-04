from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.dto.invoicing import BillingDocumentPrintout
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.invoicing.strings import BillingDocumentHtml
from app.transformers.invoicing import billing_document_texts as texts
from app.transformers.invoicing.billing_document_html import (
    render_billing_document_html,
)
from app.transformers.invoicing.billing_document_page import BillingDocumentPage
from app.transformers.invoicing.billing_document_sheet import (
    BillingDocumentSheet,
    SheetLine,
    SheetRow,
)


class BillingDocumentLayoutTransformer(
    TransformerContract[BillingDocumentPrintout, BillingDocumentHtml]
):
    """
    Lays a numbered invoice out as its invoice or its receipt, in English,
    Russian or Georgian (other languages read English, dates and amounts
    included, so one page never mixes conventions): the number and dates,
    the seller and the buyer as issued, the line with its period, the
    subtotal, the VAT and the total, the VAT note of its treatment, and how
    and when it was paid. An invoice still to pay says where to pay it.

    Raises:
        ConflictError: the invoice has no number or parties yet.
    """

    def __init__(self, localized_text_resolver: LocalizedTextResolverContract) -> None:
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def transform(self, input_data: BillingDocumentPrintout) -> BillingDocumentHtml:
        invoice: InvoiceDocument = input_data.invoice
        if invoice.number is None or invoice.seller is None or invoice.buyer is None:
            raise ConflictError("The invoice has no number yet.")

        page = BillingDocumentPage(self._localized_text_resolver, input_data)
        is_receipt: bool = input_data.kind is BillingDocumentKind.RECEIPT
        sheet = BillingDocumentSheet(
            language=str(page.language),
            title=page.say(texts.RECEIPT_TITLE if is_receipt else texts.INVOICE_TITLE),
            number=page.say(
                texts.RECEIPT_NUMBER if is_receipt else texts.NUMBER,
                number=str(invoice.number),
            ),
            status=None if is_receipt else page.say(texts.STATUS_NAMES[invoice.status]),
            facts=page.facts(is_receipt),
            seller=page.party(texts.SELLER, invoice.seller),
            buyer=page.party(texts.BUYER, invoice.buyer),
            columns=SheetLine(
                description=page.say(texts.DESCRIPTION),
                period=page.say(texts.PERIOD),
                amount=page.say(texts.AMOUNT),
            ),
            lines=[
                SheetLine(
                    description=str(invoice.description),
                    period=page.period(),
                    amount=page.money(page.subtotal_minor()),
                )
            ],
            totals=page.tax_rows(),
            grand_total=SheetRow(
                page.say(page.grand_total_label(is_receipt)),
                page.money(invoice.amount_minor),
            ),
            notes=page.notes(is_receipt),
            footer=page.say(texts.GENERATED_BY, seller=str(invoice.seller.legal_name)),
        )
        return BillingDocumentHtml(render_billing_document_html(sheet))
