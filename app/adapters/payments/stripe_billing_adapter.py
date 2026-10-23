from typed_time_provider import Microseconds, WallClock

from app.adapters.payments.payment_fields import read_reference
from app.adapters.payments.stripe_checkout_parameters import (
    MICROSECONDS_PER_SECOND,
    build_checkout_parameters,
    build_portal_parameters,
)
from app.adapters.payments.stripe_event_reader import read_stripe_event
from app.clients.stripe.stripe_client import StripeCardDeclinedError, StripeClient
from app.contracts.billing import PaymentGatewayAdapterContract
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
    PaymentStatus,
)
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
from app.schemas.exceptions.payment_errors import PaymentsNotConfiguredError
from app.schemas.typings.billing.constrained_strings import PaymentCheckoutUrl
from app.schemas.typings.billing.strings import (
    PaymentFailureReason,
    PaymentProviderReference,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl

STRIPE_WEBHOOK_PATH: str = "/v1/payments/stripe/webhook"
PAID_INVOICE_STATUS: str = "paid"


class StripeBillingAdapter(PaymentGatewayAdapterContract):
    """
    Payment gateway on Stripe Billing for the EU, the US and Israel:
    Checkout in subscription mode pays the open invoices and subscribes the
    card to the plan's automatic charges; a card setup is a Checkout that
    pays nothing now, or the billing portal's card update once the owner
    is a Stripe customer. Notifications arrive signed at
    STRIPE_WEBHOOK_PATH (`read_stripe_event` says what each one means).

    Without Stripe credentials (`stripe_client` is None) checkouts fail
    with PaymentsNotConfiguredError and notifications are refused, so
    nothing is ever marked paid unverified. A page with no return link of
    its own returns to the cabinet.
    """

    def __init__(
        self,
        stripe_client: StripeClient | None,
        cabinet_base_url: CabinetBaseUrl | None,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._stripe_client: StripeClient | None = stripe_client
        self._cabinet_base_url: CabinetBaseUrl | None = cabinet_base_url
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def create_checkout(
        self,
        request: PaymentCheckoutRequest,
    ) -> PaymentCheckoutSession:
        stripe_client: StripeClient = self._require_client()
        return_url: str = self._select_return_url(request)
        if (
            request.purpose is PaymentOrderPurpose.CARD_SETUP
            and request.customer_reference is not None
        ):
            portal: dict[str, object] = stripe_client.create_billing_portal_session(
                build_portal_parameters(str(request.customer_reference), return_url)
            )
            return PaymentCheckoutSession(
                checkout_url=read_page_url(portal), payment_reference=None
            )

        session: dict[str, object] = stripe_client.create_checkout_session(
            build_checkout_parameters(request, return_url, self._now_seconds()),
            idempotency_key=f"checkout:{request.payment_order_id}",
        )
        return PaymentCheckoutSession(
            checkout_url=read_page_url(session),
            payment_reference=read_reference(session.get("id")),
        )

    def read_notification(
        self,
        delivery: PaymentWebhookDelivery,
    ) -> VerifiedPaymentEvent:
        if self._stripe_client is None:
            raise AccessDeniedError(
                "Payment notifications cannot be verified: Stripe is not configured."
            )

        event: dict[str, object] = self._stripe_client.verify_webhook(
            str(delivery.body),
            None if delivery.signature is None else str(delivery.signature),
            self._now_seconds(),
        )
        return read_stripe_event(event, self._stripe_client)

    def stop_recurring(
        self,
        provider: PaymentProvider,
        provider_reference: PaymentProviderReference,
    ) -> None:
        self._require_client().cancel_subscription(str(provider_reference))

    def retry_charge(self, request: PaymentRetryRequest) -> PaymentRetryResult:
        """Pay the declined Stripe invoice again with the card on file."""

        if request.failed_charge_reference is None:
            raise ValidationFailedError("There is no Stripe invoice to charge again.")

        try:
            invoice: dict[str, object] = self._require_client().pay_invoice(
                str(request.failed_charge_reference),
                idempotency_key=f"retry:{request.retry_id}",
            )
        except StripeCardDeclinedError as error:
            return PaymentRetryResult(
                status=PaymentStatus.DECLINED,
                payment_reference=request.failed_charge_reference,
                failure_reason=PaymentFailureReason(error.decline_code),
            )

        return PaymentRetryResult(
            status=(
                PaymentStatus.APPROVED
                if invoice.get("status") == PAID_INVOICE_STATUS
                else PaymentStatus.PROCESSING
            ),
            payment_reference=request.failed_charge_reference,
        )

    def _select_return_url(self, request: PaymentCheckoutRequest) -> str:
        if request.return_url is not None:
            return str(request.return_url)

        if self._cabinet_base_url is None:
            raise PaymentsNotConfiguredError(
                "Stripe pages need a return link (CABINET_BASE_URL)."
            )

        return str(self._cabinet_base_url).rstrip("/") + "/"

    def _now_seconds(self) -> int:
        return int(self._wall_clock.now_unix()) // MICROSECONDS_PER_SECOND

    def _require_client(self) -> StripeClient:
        if self._stripe_client is None:
            raise PaymentsNotConfiguredError(
                "Stripe payments are not configured (STRIPE_SECRET_KEY, "
                "STRIPE_WEBHOOK_SECRET)."
            )

        return self._stripe_client


def read_page_url(session: dict[str, object]) -> PaymentCheckoutUrl:
    try:
        return PaymentCheckoutUrl(str(session.get("url")))
    except (TypeError, ValueError) as error:
        raise ExternalServiceError(
            "Stripe did not return a payment page link."
        ) from error
