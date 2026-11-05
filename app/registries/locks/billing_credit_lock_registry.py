from contextlib import AbstractContextManager

from app.contracts.billing_credits import BillingCreditLockRegistryContract
from app.contracts.locks import AdvisoryLockAdapterContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

BILLING_CREDIT_LOCK_PURPOSE: str = "billing-credits"
# The locked section reads a business's ledger and invoices and writes one
# invoice and one ledger line: well under a second.
BILLING_CREDIT_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(10)


class BillingCreditLockRegistry(BillingCreditLockRegistryContract):
    """
    One lock per business around the use of its credit, so two invoices
    issued at the same moment (a checkout and the renewal job, in any API
    instance or worker) never spend the same credit twice.

    Transaction-held (`hold_with_transaction`): the invoice and the ledger
    line written in the block are committed when the next holder reads the
    balance.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        return self._advisory_locks.hold_with_transaction(
            AdvisoryLockKey(f"{BILLING_CREDIT_LOCK_PURPOSE}|{business_id}"),
            BILLING_CREDIT_LOCK_WAIT,
        )
