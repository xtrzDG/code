"""Every document of one business, a keyset page at a time (full exports)."""

from typing import Protocol

from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId


class BusinessDocumentPagesContract[Document](Protocol):
    """
    The pages of a business's documents in the order they were first
    written: after the window's position (its item key alone, no sort
    values), at most its limit. Every tenant repository offers it
    (`BusinessScopedRepository.page_in_write_order`), so a full export
    streams any collection in bounded pages instead of loading it whole.
    """

    def page_in_write_order(
        self, business_id: BusinessId, window: KeysetSlice
    ) -> list[Document]:
        raise NotImplementedError
