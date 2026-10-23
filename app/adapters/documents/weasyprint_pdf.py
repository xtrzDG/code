import logging

from app.schemas.exceptions.application_errors import ExternalServiceError

logger: logging.Logger = logging.getLogger(__name__)

# No URL scheme is allowed: the page references nothing outside itself, so
# a value that slipped a link in could never make the engine fetch it.
NO_PROTOCOLS: tuple[str, ...] = ()


def render_pdf(html: str) -> bytes:
    """
    A self-contained page as a PDF with WeasyPrint (Pango lays out Latin,
    Cyrillic, Georgian and Hebrew with the system's Noto fonts; the
    Dockerfile installs them). WeasyPrint is loaded on the first document,
    so the API starts even where its system libraries are missing; then
    rendering fails with ExternalServiceError (the cabinet shows "try
    again").
    """

    try:
        from weasyprint import HTML
        from weasyprint.urls import URLFetcher

        return HTML(
            string=html,
            url_fetcher=URLFetcher(allowed_protocols=NO_PROTOCOLS),
        ).write_pdf()
    except Exception as error:
        logger.exception("The PDF engine failed.")
        raise ExternalServiceError(
            "The PDF could not be made; please try again later."
        ) from error
