from collections.abc import Sequence

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.exchange_rate_repositories import (
    ExchangeRateRepoContract,
)
from app.schemas.domain.exchange_rates import ExchangeRateDocument
from app.schemas.dto.storage_pages import DocumentLatestQuery
from app.schemas.typings.billing.constrained_strings import CurrencyPairCode
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText

PAIR_FIELD: DocumentFieldPath = DocumentFieldPath("pair")
RATE_DAY_FIELD: DocumentFieldPath = DocumentFieldPath("rate_day")


class ExchangeRateRepository(ExchangeRateRepoContract):
    """
    Dated exchange rates (platform-wide). A rate is stored under its source,
    pair and day ("ecb:EUR/USD:2026-10-02"), so a refresh that runs again
    on the same day replaces it; the newest of a pair is one indexed probe
    of (pair, rate_day) (migration 1071).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[ExchangeRateDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[ExchangeRateDocument] = (
            collection
        )

    def save_many(self, rates: Sequence[ExchangeRateDocument]) -> DocumentCount:
        self._collection.upsert_many([(rate_key(rate), rate) for rate in rates])
        return DocumentCount(len(rates))

    def find_latest(
        self,
        pairs: Sequence[CurrencyPairCode],
    ) -> list[ExchangeRateDocument]:
        if not pairs:
            return []

        return self._collection.latest_by(
            DocumentLatestQuery(
                group_field=PAIR_FIELD,
                groups=tuple(DocumentFieldText(str(pair)) for pair in pairs),
                sort_field=RATE_DAY_FIELD,
            )
        )


def rate_key(rate: ExchangeRateDocument) -> str:
    return f"{rate.source}:{rate.pair}:{rate.rate_date}"
