import logging

from app.contracts.invoicing import InvoiceDocumentRendererContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.invoicing.strings import BillingDocumentHtml

logger: logging.Logger = logging.getLogger(__name__)

# No URL scheme is allowed: the page references nothing outside itself, so
# a value that slipped a link in could never make the engine fetch it.
NO_PROTOCOLS: tuple[str, ...] = ()


class WeasyPrintInvoiceDocumentRendererAdapter(InvoiceDocumentRendererContract):
    """
    Invoice and receipt PDFs with WeasyPrint (Pango lays out Latin,
    Cyrillic and Georgian with the system's Noto fonts; the Dockerfile
    installs them). WeasyPrint is loaded on the first document, so the API
    starts even where its system libraries are missing; then rendering
    fails with ExternalServiceError (the cabinet shows "try again").
    """

    def render(self, html: BillingDocumentHtml) -> bytes:
        try:
            from weasyprint import HTML
            from weasyprint.urls import URLFetcher

            return HTML(
                string=str(html),
                url_fetcher=URLFetcher(allowed_protocols=NO_PROTOCOLS),
            ).write_pdf()
        except Exception as error:
            logger.exception("The PDF engine failed.")
            raise ExternalServiceError(
                "The PDF could not be made; please try again later."
            ) from error
