"""
Invoice numbers on both storages: each series counts from 1 every year,
and issuers taking numbers at the same moment, in many threads, each get
another one with none left out (compare-and-set on the counter row).
"""

import threading

from typed_time_provider import Microseconds

from app.repositories.invoicing_repositories import InvoiceCounterRepository
from app.schemas.domain.billing_profiles import InvoiceCounterDocument
from app.schemas.typings.invoicing.constrained_integers import InvoiceYear
from app.schemas.typings.invoicing.constrained_strings import InvoiceSeries
from tests.storage.concurrency_limits import THREAD_COUNT, WRITES_PER_THREAD
from tests.storage.conftest import CollectionFactory

NOW: Microseconds = Microseconds(1_790_845_200_000_000)
SERIES: InvoiceSeries = InvoiceSeries("AW")
YEAR: InvoiceYear = InvoiceYear(2026)


def counter_repo(collections: CollectionFactory) -> InvoiceCounterRepository:
    return InvoiceCounterRepository(
        collections(InvoiceCounterDocument, "invoice_counters")
    )


def test_each_series_counts_from_one_every_year(
    collections: CollectionFactory,
) -> None:
    counters = counter_repo(collections)

    taken = [int(counters.take_next(SERIES, YEAR, NOW)) for _ in range(3)]
    next_year = int(counters.take_next(SERIES, InvoiceYear(2027), NOW))
    other_series = int(counters.take_next(InvoiceSeries("TEST"), YEAR, NOW))
    after = int(counters.take_next(SERIES, YEAR, NOW))

    assert taken == [1, 2, 3]
    assert (next_year, other_series, after) == (1, 1, 4)


def test_concurrent_issuers_never_share_a_number(
    collections: CollectionFactory,
) -> None:
    counters = counter_repo(collections)
    start = threading.Barrier(THREAD_COUNT)
    numbers: list[int] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def issue() -> None:
        try:
            start.wait()
            for _ in range(WRITES_PER_THREAD):
                number = int(counters.take_next(SERIES, YEAR, NOW))
                with lock:
                    numbers.append(number)
        except BaseException as error:  # reported by the main thread
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=issue) for _ in range(THREAD_COUNT)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert sorted(numbers) == list(range(1, THREAD_COUNT * WRITES_PER_THREAD + 1))
    assert int(counters.take_next(SERIES, YEAR, NOW)) == len(numbers) + 1
