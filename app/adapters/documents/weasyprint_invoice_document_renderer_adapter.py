from app.adapters.documents.weasyprint_pdf import render_pdf
from app.contracts.invoicing import InvoiceDocumentRendererContract
from app.schemas.typings.invoicing.strings import BillingDocumentHtml


class WeasyPrintInvoiceDocumentRendererAdapter(InvoiceDocumentRendererContract):
    """Invoice and receipt PDFs with WeasyPrint (`render_pdf`)."""

    def render(self, html: BillingDocumentHtml) -> bytes:
        return render_pdf(str(html))
