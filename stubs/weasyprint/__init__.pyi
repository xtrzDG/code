# Typed surface of WeasyPrint (no inline types upstream) that the invoice
# renderer uses: HTML from a string, written to PDF bytes.
from weasyprint.urls import URLFetcher

class HTML:
    def __init__(
        self,
        *,
        string: str,
        base_url: str | None = ...,
        url_fetcher: URLFetcher | None = ...,
        media_type: str = ...,
    ) -> None: ...
    def write_pdf(self) -> bytes: ...
