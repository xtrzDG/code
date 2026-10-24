"""Billing seams: payment orders, package usage warnings, the payment gateway."""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.repo_contract import RepoContract
from app.schemas.constants.billing import PackageMetric
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payment_retries import PaymentRetryRequest, PaymentRetryResult
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    PaymentWebhookDelivery,
    VerifiedPaymentEvent,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId, SubscriptionId
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId

type PaymentOrderChange = Callable[[PaymentOrderDocument], PaymentOrderDocument | None]


class PaymentOrderRepoContract(RepoContract, Protocol):
    def save(self, payment_order: PaymentOrderDocument) -> None:
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        payment_order_id: PaymentOrderId,
        change: PaymentOrderChange,
    ) -> PaymentOrderDocument | None:
        """
        Apply `change` to the stored order atomically (it returns None to
        keep the order as it is); None when there is no such order.
        """
        raise NotImplementedError

    def get(self, payment_order_id: PaymentOrderId) -> PaymentOrderDocument | None:
        """
        Look up by id alone: provider notifications carry only the order id,
        and their signature is verified before the lookup.
        """
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[PaymentOrderDocument]:
        """Return payment orders ordered by created_at descending."""
        raise NotImplementedError


class PackageUsageWarningRepoContract(RepoContract, Protocol):
    def save(self, warning: PackageUsageWarningDocument) -> None:
        raise NotImplementedError

    def find(
        self,
        business_id: BusinessId,
        subscription_id: SubscriptionId,
        metric: PackageMetric,
        period_start: Microseconds,
    ) -> PackageUsageWarningDocument | None:
        raise NotImplementedError


class PaymentGatewayAdapterContract(AdapterContract, Protocol):
    def create_checkout(
        self,
        request: PaymentCheckoutRequest,
    ) -> PaymentCheckoutSession:
        """
        Create a hosted page of `request.provider`: a payment with automatic
        charges afterwards, or (CARD_SETUP) a page that only saves the card
        for them.

        Raises:
            ExternalServiceError: the provider is not configured, unreachable,
                or refused the request.
        """
        raise NotImplementedError

    def read_notification(
        self,
        delivery: PaymentWebhookDelivery,
    ) -> VerifiedPaymentEvent:
        """
        Verify and decode a notification of `delivery.provider`: a
        payment's status, a saved card, both, or neither (an event the
        platform does not act on).

        Raises:
            AccessDeniedError: the signature or merchant does not match, or
                notifications cannot be verified because the provider is not
                configured.
            ValidationFailedError: the body is malformed.
        """
        raise NotImplementedError

    def stop_recurring(
        self,
        provider: PaymentProvider,
        provider_reference: PaymentProviderReference,
    ) -> None:
        """
        Stop the automatic charges a checkout started at that provider.

        Raises:
            ExternalServiceError: the provider failed or is not configured.
        """
        raise NotImplementedError

    def retry_charge(self, request: PaymentRetryRequest) -> PaymentRetryResult:
        """
        Charge the saved card again for an unpaid invoice (dunning); a
        request repeated with the same `retry_id` charges once.

        Raises:
            ExternalServiceError: the provider failed or is not configured.
            ValidationFailedError: nothing to charge again with (no saved
                card token or provider charge for this provider).
        """
        raise NotImplementedError
