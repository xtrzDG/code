from typed_time_provider import Microseconds, WallClock

from app.adapters.payments.flitt_notification_reader import (
    read_flitt_event,
    read_payment_status,
)
from app.adapters.payments.flitt_order_parameters import (
    build_checkout_order,
    build_retry_order,
)
from app.adapters.payments.payment_fields import (
    read_failure_reason,
    read_reference,
)
from app.clients.flitt.flitt_client import FlittClient
from app.contracts.billing import PaymentGatewayAdapterContract
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.dto.payment_retries import PaymentRetryRequest, PaymentRetryResult
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    PaymentWebhookDelivery,
    VerifiedPaymentEvent,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_strings import PaymentCheckoutUrl
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl

FLITT_WEBHOOK_PATH: str = "/v1/payments/flitt/webhook"


class FlittPaymentGatewayAdapter(PaymentGatewayAdapterContract):
    """
    Payment gateway on Flitt (Georgia and Armenia): a hosted page that
    charges the open invoices and subscribes the card to automatic monthly
    or annual charges, a card setup page that verifies the card for
    nothing and subscribes it, and charges of the saved card's token for
    the retries of a declined automatic charge.

    Without Flitt credentials (`flitt_client` is None) or a public base URL
    for callbacks, checkouts fail with ExternalServiceError and
    notifications are refused, so nothing is ever marked paid unverified.
    """

    def __init__(
        self,
        flitt_client: FlittClient | None,
        app_base_url: PublicBaseUrl | None,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._flitt_client: FlittClient | None = flitt_client
        self._app_base_url: PublicBaseUrl | None = app_base_url
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def create_checkout(
        self,
        request: PaymentCheckoutRequest,
    ) -> PaymentCheckoutSession:
        flitt_client: FlittClient = self._require_client()
        response: dict[str, object] = flitt_client.create_checkout_url(
            build_checkout_order(request, self._callback_url())
        )
        raw_checkout_url: object = response.get("checkout_url")
        try:
            checkout_url = PaymentCheckoutUrl(str(raw_checkout_url))
        except (TypeError, ValueError) as error:
            raise ExternalServiceError(
                "Flitt did not return a payment page link."
            ) from error

        return PaymentCheckoutSession(
            checkout_url=checkout_url,
            payment_reference=read_reference(response.get("payment_id")),
        )

    def read_notification(
        self,
        delivery: PaymentWebhookDelivery,
    ) -> VerifiedPaymentEvent:
        if self._flitt_client is None:
            raise AccessDeniedError(
                "Payment notifications cannot be verified: Flitt is not configured."
            )

        parameters: dict[str, object] = self._flitt_client.verify_callback(
            str(delivery.body),
            None if delivery.content_type is None else str(delivery.content_type),
        )
        return read_flitt_event(parameters, self._wall_clock.now_unix())

    def stop_recurring(
        self,
        provider: PaymentProvider,
        provider_reference: PaymentProviderReference,
    ) -> None:
        self._require_client().stop_subscription(str(provider_reference))

    def retry_charge(self, request: PaymentRetryRequest) -> PaymentRetryResult:
        """Charge the saved card's token; Flitt answers with the status."""

        if request.card_token is None:
            raise ValidationFailedError("There is no saved card to charge again.")

        response: dict[str, object] = self._require_client().charge_recurring(
            build_retry_order(request, str(request.card_token), self._callback_url())
        )
        status: PaymentStatus = read_payment_status(response.get("order_status"))
        return PaymentRetryResult(
            status=status,
            payment_reference=read_reference(response.get("payment_id")),
            failure_reason=(
                read_failure_reason(response.get("response_description"))
                if status is not PaymentStatus.APPROVED
                else None
            ),
        )

    def _callback_url(self) -> str:
        if self._app_base_url is None:
            raise ExternalServiceError(
                "Online payments need APP_BASE_URL for payment notifications."
            )

        return f"{str(self._app_base_url).rstrip('/')}{FLITT_WEBHOOK_PATH}"

    def _require_client(self) -> FlittClient:
        if self._flitt_client is None:
            raise ExternalServiceError(
                "Online payments are not configured (FLITT_MERCHANT_ID, "
                "FLITT_SECRET_KEY)."
            )

        return self._flitt_client
