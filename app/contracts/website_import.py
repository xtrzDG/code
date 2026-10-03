"""The website reader: facts of one page of a business's site, for review."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.website_import import (
    WebsitePageExtraction,
    WebsitePageExtractionRequest,
)


class WebsiteExtractionAdapterContract(AdapterContract, Protocol):
    def extract(self, request: WebsitePageExtractionRequest) -> WebsitePageExtraction:
        """
        Read the FAQ, policies (opening hours, delivery, payment) and the
        offer (menu items, services, rooms, products with their written
        prices) stated on one page. The page text is untrusted: it reaches
        the model fenced, as data. Nothing is invented: a page without facts
        gives no items.

        An answer that is not the requested JSON is returned as unreadable
        (with the tokens it cost), not raised.

        Raises:
            ExternalServiceError: the model is unavailable (LlmRefusedError:
                it declined).
        """
        raise NotImplementedError
