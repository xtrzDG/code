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
    One row per invoice series and year. A number is taken under the row's
    lock: the row is read and moved on by one in one step, so issuers at the
    same moment wait for each other instead of retrying (retries can lose
    many times in a row under load). The first number of a series and year
    inserts the row only if it is absent; an issuer that lost that race
    takes the next number from the row the winner inserted.
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
        taken: InvoiceSequenceNumber | None = self._advance(key, now)
        if taken is not None:
            return taken

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

        taken = self._advance(key, now)
        if taken is None:
            raise ConflictError(
                "The invoice counter disappeared while a number was taken."
            )

        return taken

    def _advance(
        self, key: InvoiceCounterKey, now: Microseconds
    ) -> InvoiceSequenceNumber | None:
        """The number after the stored one, or None when there is no row yet."""

        advanced: InvoiceCounterDocument | None = self._collection.modify(
            str(key),
            lambda stored: stored.model_copy(
                update={
                    "last_number": InvoiceSequenceNumber(int(stored.last_number) + 1),
                    "updated_at": now,
                }
            ),
        )
        return None if advanced is None else advanced.last_number
