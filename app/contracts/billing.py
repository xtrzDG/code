"""Billing seams: payment orders, package usage warnings, the payment gateway."""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.repo_contract import RepoContract
from app.schemas.constants.billing import PackageMetric
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    PaymentNotification,
    PaymentWebhookDelivery,
)
from app.schemas.typings.billing.prefixed_id import PaymentOrderId, SubscriptionId
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId


class PaymentOrderRepoContract(RepoContract, Protocol):
    def save(self, payment_order: PaymentOrderDocument) -> None:
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
        Create a hosted payment page with automatic charges afterwards.

        Raises:
            ExternalServiceError: the provider is not configured, unreachable,
                or refused the request.
        """
        raise NotImplementedError

    def read_notification(
        self,
        delivery: PaymentWebhookDelivery,
    ) -> PaymentNotification:
        """
        Verify and decode a provider notification.

        Raises:
            AccessDeniedError: the signature or merchant does not match, or
                notifications cannot be verified because the provider is not
                configured.
            ValidationFailedError: the body is malformed.
        """
        raise NotImplementedError

    def stop_recurring(self, provider_reference: PaymentProviderReference) -> None:
        """
        Stop the automatic charges started by a checkout.

        Raises:
            ExternalServiceError: the provider failed or is not configured.
        """
        raise NotImplementedError
