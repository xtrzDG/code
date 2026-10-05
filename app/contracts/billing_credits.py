"""The lock that keeps two invoices of one business from using the same credit."""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.typings.businesses.prefixed_id import BusinessId


class BillingCreditLockRegistryContract(RegistryContract, Protocol):
    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        """
        Lock serializing the use of one business's credit across every
        process: the balance read, the invoice and the ledger line written
        in the block commit together before the next holder reads.
        """
        raise NotImplementedError
