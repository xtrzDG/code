from app.contracts.invoicing import (
    BillingDocumentFacilitatorContract,
    InvoiceDocumentRendererContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.invoicing import BillingDocumentFile, BillingDocumentPrintout
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.invoicing.constrained_strings import (
    BillingDocumentFileName,
    InvoiceNumber,
)
from app.schemas.typings.invoicing.strings import BillingDocumentHtml
from app.schemas.typings.localization.constrained_strings import LanguageTag


class BillingDocumentFacilitator(BillingDocumentFacilitatorContract):
    """
    The PDF of an invoice or its receipt: laid out in the reader's language
    (dates in the business's time zone), rendered, and named after the
    number ("invoice-AW-2026-000042.pdf", "receipt-AW-2026-000042.pdf").
    Shared by the cabinet download and the e-mails to the billing contact.
    """

    def __init__(
        self,
        layout_transformer: TransformerContract[
            BillingDocumentPrintout, BillingDocumentHtml
        ],
        renderer: InvoiceDocumentRendererContract,
    ) -> None:
        self._layout_transformer: TransformerContract[
            BillingDocumentPrintout, BillingDocumentHtml
        ] = layout_transformer
        self._renderer: InvoiceDocumentRendererContract = renderer

    def produce(
        self,
        business: BusinessDocument,
        invoice: InvoiceDocument,
        kind: BillingDocumentKind,
        language: LanguageTag,
    ) -> BillingDocumentFile:
        number: InvoiceNumber | None = invoice.number
        if number is None:
            raise ConflictError("The invoice has no number yet.")

        if kind is BillingDocumentKind.RECEIPT and invoice.status is not (
            InvoiceStatus.PAID
        ):
            raise ConflictError("The invoice is not paid, so it has no receipt.")

        html: BillingDocumentHtml = self._layout_transformer.transform(
            BillingDocumentPrintout(
                invoice=invoice,
                kind=kind,
                language=language,
                timezone=business.timezone,
            )
        )
        return BillingDocumentFile(
            file_name=BillingDocumentFileName(f"{kind.value}-{number}.pdf"),
            content=self._renderer.render(html),
        )
