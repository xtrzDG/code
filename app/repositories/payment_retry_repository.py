from app.contracts.payment_methods import PaymentRetryRepoContract
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument
from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.schemas.typings.billing.prefixed_id import InvoiceId, PaymentRetryId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.billing.payment_retry_identity import derive_payment_retry_id

FIRST_RETRY_ATTEMPT: int = 1
LAST_RETRY_ATTEMPT: int = 3


class PaymentRetryRepository(
    BusinessScopedRepository[PaymentRetryAttemptDocument],
    PaymentRetryRepoContract,
):
    """
    Retries of declined automatic charges keyed by their derived ids
    (invoice and attempt), so an invoice's retries are read by id in one
    read and a retry is claimed by inserting its row only if absent.
    """

    def claim(self, attempt: PaymentRetryAttemptDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(attempt.id), attempt))

    def save(self, attempt: PaymentRetryAttemptDocument) -> None:
        self._store(str(attempt.id), attempt)

    def get(
        self, business_id: BusinessId, retry_id: PaymentRetryId
    ) -> PaymentRetryAttemptDocument | None:
        return self._load(business_id, str(retry_id))

    def list_for_invoice(
        self, business_id: BusinessId, invoice_id: InvoiceId
    ) -> list[PaymentRetryAttemptDocument]:
        attempts: list[PaymentRetryAttemptDocument] = self._load_many(
            business_id,
            [
                str(derive_payment_retry_id(invoice_id, PaymentRetryAttempt(attempt)))
                for attempt in range(FIRST_RETRY_ATTEMPT, LAST_RETRY_ATTEMPT + 1)
            ],
        )
        return sorted(attempts, key=lambda attempt: int(attempt.attempt))
