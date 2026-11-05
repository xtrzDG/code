"""Seams of the card on file and dunning: who charges, retries, owner notices."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.registry_contract import RegistryContract
from app.contracts.repo_contract import RepoContract
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument
from app.schemas.dto.payment_retries import DunningNotice
from app.schemas.typings.billing.constrained_integers import DunningRecipientCount
from app.schemas.typings.billing.prefixed_id import InvoiceId, PaymentRetryId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CountryCode


class PaymentProviderRegistryContract(RegistryContract, Protocol):
    def select(self, country_code: CountryCode) -> PaymentProvider:
        """
        The provider that charges businesses of a country: its region's
        provider when that one is configured and may be stored, else the
        one that is.
        """
        raise NotImplementedError


class PaymentRetryRepoContract(RepoContract, Protocol):
    def claim(self, attempt: PaymentRetryAttemptDocument) -> bool:
        """
        Store the retry only if no worker claimed it before (its id derives
        from the invoice and the attempt); True when this call claimed it.
        """
        raise NotImplementedError

    def save(self, attempt: PaymentRetryAttemptDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, retry_id: PaymentRetryId
    ) -> PaymentRetryAttemptDocument | None:
        raise NotImplementedError

    def list_for_invoice(
        self, business_id: BusinessId, invoice_id: InvoiceId
    ) -> list[PaymentRetryAttemptDocument]:
        """The retries of an invoice, first attempt first (one read)."""
        raise NotImplementedError


class DunningNoticeFacilitatorContract(FacilitatorContract, Protocol):
    def send(
        self, business: BusinessDocument, notice: DunningNotice
    ) -> DunningRecipientCount:
        """
        Queue the notice in the outbox for the owners' e-mail addresses and
        the business's Telegram chats linked to the platform bot, each in
        its language, with a signed link to the billing page; each address
        gets one notice per retry however often it is queued. Returns how
        many were queued. Never raises.
        """
        raise NotImplementedError
