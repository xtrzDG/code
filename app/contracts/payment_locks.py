"""The lock around applying one payment order's provider notifications."""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class PaymentNotificationLockRegistryContract(RegistryContract, Protocol):
    def lock_for_order(
        self, business_id: BusinessId, payment_order_id: PaymentOrderId
    ) -> AbstractContextManager[object]:
        """
        Lock serializing the notifications of one payment order across
        every process (each API instance takes provider webhooks): the
        order is read, checked against the notifications it already
        applied, changed and stored by one holder at a time, so two copies
        of one delivery that arrive together apply once. Held for a block
        that may call the provider (reading a payment back, stopping a
        stray schedule); each storage write of the block commits on its own.
        """
        raise NotImplementedError
