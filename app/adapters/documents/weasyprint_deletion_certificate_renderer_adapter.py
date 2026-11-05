from app.adapters.documents.weasyprint_pdf import render_pdf
from app.contracts.deletion_certificates import DeletionCertificateRendererContract
from app.schemas.typings.business_closures.strings import DeletionCertificateHtml


class WeasyPrintDeletionCertificateRendererAdapter(DeletionCertificateRendererContract):
    """Deletion certificate PDFs with WeasyPrint (`render_pdf`)."""

    def render(self, html: DeletionCertificateHtml) -> bytes:
        return render_pdf(str(html))
