from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.invoicing import (
    BillingProfileRepoContract,
    InvoiceCounterRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.billing_profiles import (
    BillingProfileDocument,
    InvoiceCounterDocument,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.invoicing.constrained_integers import (
    InvoiceSequenceNumber,
    InvoiceYear,
)
from app.schemas.typings.invoicing.constrained_strings import (
    InvoiceCounterKey,
    InvoiceSeries,
)
from app.utilities.billing.invoicing_keys import (
    build_counter_key,
    derive_billing_profile_id,
)

# Attempts before a number is given up as contended (each lost attempt
# means another invoice got the number in between).
MAX_COUNTER_ATTEMPTS: int = 50
FIRST_NUMBER: InvoiceSequenceNumber = InvoiceSequenceNumber(1)


class BillingProfileRepository(
    BusinessScopedRepository[BillingProfileDocument],
    BillingProfileRepoContract,
):
    """Billing details keyed by their derived id: one per business."""

    def get_by_business(self, business_id: BusinessId) -> BillingProfileDocument | None:
        return self._load(business_id, str(derive_billing_profile_id(business_id)))

    def save(self, profile: BillingProfileDocument) -> None:
        self._store(str(profile.id), profile)


class InvoiceCounterRepository(InvoiceCounterRepoContract):
    """
    One row per invoice series and year. A number is taken by
    compare-and-set: the first number inserts the row only if it is absent,
    every later one replaces the row only while its `last_number` is still
    the one read; a lost race reads again and retries.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[InvoiceCounterDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[InvoiceCounterDocument] = (
            collection
        )

    def take_next(
        self, series: InvoiceSeries, year: InvoiceYear, now: Microseconds
    ) -> InvoiceSequenceNumber:
        key: InvoiceCounterKey = build_counter_key(series, year)
        for _ in range(MAX_COUNTER_ATTEMPTS):
            current: InvoiceCounterDocument | None = self._collection.get(str(key))
            if current is None:
                first = InvoiceCounterDocument(
                    id=key,
                    series=series,
                    year=year,
                    last_number=FIRST_NUMBER,
                    created_at=now,
                    updated_at=now,
                )
                if self._collection.insert_if_absent(str(key), first):
                    return FIRST_NUMBER

                continue

            taken: InvoiceSequenceNumber | None = self._advance(key, current, now)
            if taken is not None:
                return taken

        raise ConflictError(
            "Invoice numbers are being taken too fast; try again in a moment."
        )

    def _advance(
        self,
        key: InvoiceCounterKey,
        current: InvoiceCounterDocument,
        now: Microseconds,
    ) -> InvoiceSequenceNumber | None:
        """The number after `current`, or None when another writer won."""

        read_number: InvoiceSequenceNumber = current.last_number
        following = InvoiceSequenceNumber(int(read_number) + 1)
        advanced: InvoiceCounterDocument = current.model_copy(
            update={"last_number": following, "updated_at": now}
        )
        is_taken: bool = self._collection.replace_if(
            str(key),
            advanced,
            lambda stored: stored.last_number == read_number,
        )
        return following if is_taken else None
