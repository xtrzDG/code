"""
Two issuers taking the first number of a series and year at once: the one
whose insert of the counter row loses takes the next number from the row
the other one inserted.
"""

import pytest
from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.invoicing_repositories import InvoiceCounterRepository
from app.schemas.domain.billing_profiles import InvoiceCounterDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.invoicing.constrained_integers import InvoiceYear
from app.schemas.typings.invoicing.constrained_strings import InvoiceSeries
from app.schemas.typings.storage.booleans import IsDocumentInserted

NOW: Microseconds = Microseconds(1_790_845_200_000_000)
SERIES: InvoiceSeries = InvoiceSeries("AW")
YEAR: InvoiceYear = InvoiceYear(2026)


class OtherIssuerInsertsFirst(
    InMemoryDocumentCollectionAdapter[InvoiceCounterDocument]
):
    """The other issuer's row lands just before this issuer's insert."""

    def insert_if_absent(
        self, document_key: str, document: InvoiceCounterDocument
    ) -> IsDocumentInserted:
        super().insert_if_absent(document_key, document)
        return False


class RowNeverLands(InMemoryDocumentCollectionAdapter[InvoiceCounterDocument]):
    """An insert that loses, yet no row is there afterwards."""

    def insert_if_absent(
        self, document_key: str, document: InvoiceCounterDocument
    ) -> IsDocumentInserted:
        return False


def test_the_issuer_that_loses_the_first_insert_takes_the_second_number() -> None:
    counters = InvoiceCounterRepository(OtherIssuerInsertsFirst(InvoiceCounterDocument))

    assert int(counters.take_next(SERIES, YEAR, NOW)) == 2
    assert int(counters.take_next(SERIES, YEAR, NOW)) == 3


def test_a_counter_row_that_never_lands_is_a_conflict() -> None:
    counters = InvoiceCounterRepository(RowNeverLands(InvoiceCounterDocument))

    with pytest.raises(ConflictError):
        counters.take_next(SERIES, YEAR, NOW)
