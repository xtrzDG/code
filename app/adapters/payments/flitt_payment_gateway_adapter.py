from app.clients.flitt.flitt_client import FlittClient
from app.contracts.billing import PaymentGatewayAdapterContract
from app.schemas.constants.payments import PaymentProvider, PaymentStatus
from app.schemas.dto.billing import Money
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    PaymentNotification,
    PaymentWebhookDelivery,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.constrained_strings import PaymentCheckoutUrl
from app.schemas.typings.billing.strings import (
    PaymentFailureReason,
    PaymentProviderReference,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.localization.language_tags import split_language_tag_text

FLITT_WEBHOOK_PATH: str = "/v1/payments/flitt/webhook"
# Payment page languages listed for the Flitt `lang` parameter.
FLITT_PAGE_LANGUAGES: frozenset[str] = frozenset(
    {
        "az",
        "cs",
        "da",
        "de",
        "en",
        "es",
        "fi",
        "fr",
        "hu",
        "it",
        "ka",
        "ko",
        "lv",
        "nl",
        "pl",
        "ro",
        "ru",
        "sk",
        "uk",
        "zh",
    }
)
RECURRING_PERIOD_UNIT: str = "month"
FLAG_YES: str = "y"
SUBSCRIPTION_FLAG: str = "Y"
MAX_ORDER_DESCRIPTION_LENGTH: int = 1024
MAX_FAILURE_REASON_LENGTH: int = 300
FAILED_STATUSES: frozenset[PaymentStatus] = frozenset(
    {PaymentStatus.DECLINED, PaymentStatus.EXPIRED}
)


class FlittPaymentGatewayAdapter(PaymentGatewayAdapterContract):
    """
    Payment gateway on Flitt: a hosted page that charges the open invoices
    and subscribes the card to automatic monthly or annual charges.

    Without Flitt credentials (`flitt_client` is None) or a public base URL
    for callbacks, checkouts fail with ExternalServiceError and
    notifications are refused, so nothing is ever marked paid unverified.
    """

    def __init__(
        self,
        flitt_client: FlittClient | None,
        app_base_url: PublicBaseUrl | None,
    ) -> None:
        self._flitt_client: FlittClient | None = flitt_client
        self._app_base_url: PublicBaseUrl | None = app_base_url

    def create_checkout(
        self,
        request: PaymentCheckoutRequest,
    ) -> PaymentCheckoutSession:
        flitt_client: FlittClient = self._require_client()
        if self._app_base_url is None:
            raise ExternalServiceError(
                "Online payments need APP_BASE_URL for payment notifications."
            )

        callback_url: str = f"{str(self._app_base_url).rstrip('/')}{FLITT_WEBHOOK_PATH}"
        order_parameters: dict[str, object] = {
            "order_id": str(request.payment_order_id),
            "order_desc": str(request.description)[:MAX_ORDER_DESCRIPTION_LENGTH],
            "amount": int(request.amount.amount_minor),
            "currency": str(request.amount.currency_code),
            "server_callback_url": callback_url,
            "merchant_data": str(request.payment_order_id),
            "subscription": SUBSCRIPTION_FLAG,
            "subscription_callback_url": callback_url,
            "recurring_data": {
                "every": int(request.recurring_charge.interval_months),
                "period": RECURRING_PERIOD_UNIT,
                "amount": int(request.recurring_charge.amount.amount_minor),
                "start_time": str(request.recurring_charge.start_date),
                "state": FLAG_YES,
                "readonly": FLAG_YES,
            },
        }
        page_language: str | None = select_page_language(request.language)
        if page_language is not None:
            order_parameters["lang"] = page_language

        if request.return_url is not None:
            order_parameters["response_url"] = str(request.return_url)

        response: dict[str, object] = flitt_client.create_checkout_url(order_parameters)
        raw_checkout_url: object = response.get("checkout_url")
        try:
            checkout_url = PaymentCheckoutUrl(str(raw_checkout_url))
        except (TypeError, ValueError) as error:
            raise ExternalServiceError(
                "Flitt did not return a payment page link."
            ) from error

        raw_payment_id: object = response.get("payment_id")
        return PaymentCheckoutSession(
            checkout_url=checkout_url,
            payment_reference=read_reference(raw_payment_id),
        )

    def read_notification(
        self,
        delivery: PaymentWebhookDelivery,
    ) -> PaymentNotification:
        if self._flitt_client is None:
            raise AccessDeniedError(
                "Payment notifications cannot be verified: Flitt is not configured."
            )

        parameters: dict[str, object] = self._flitt_client.verify_callback(
            str(delivery.body),
            None if delivery.content_type is None else str(delivery.content_type),
        )
        order_reference: PaymentProviderReference | None = read_reference(
            parameters.get("order_id")
        )
        if order_reference is None:
            raise ValidationFailedError("Payment notification has no order id.")

        status: PaymentStatus = read_payment_status(parameters.get("order_status"))
        return PaymentNotification(
            provider=PaymentProvider.FLITT,
            order_reference=order_reference,
            parent_order_reference=read_reference(parameters.get("parent_order_id")),
            merchant_reference=read_reference(parameters.get("merchant_data")),
            payment_reference=read_reference(parameters.get("payment_id")),
            status=status,
            amount=read_money(parameters.get("amount"), parameters.get("currency")),
            failure_reason=(
                read_failure_reason(parameters.get("response_description"))
                if status in FAILED_STATUSES
                else None
            ),
        )

    def stop_recurring(self, provider_reference: PaymentProviderReference) -> None:
        self._require_client().stop_subscription(str(provider_reference))

    def _require_client(self) -> FlittClient:
        if self._flitt_client is None:
            raise ExternalServiceError(
                "Online payments are not configured (FLITT_MERCHANT_ID, "
                "FLITT_SECRET_KEY)."
            )

        return self._flitt_client


def select_page_language(language_tag: LanguageTag) -> str | None:
    """Flitt page language for a tag ("ka-GE" -> "ka"), if Flitt has it."""

    language: str = split_language_tag_text(str(language_tag)).language
    return language if language in FLITT_PAGE_LANGUAGES else None


def read_reference(raw_value: object) -> PaymentProviderReference | None:
    """A provider identifier sent as text or number; empty means absent."""

    if isinstance(raw_value, bool) or raw_value is None:
        return None

    if isinstance(raw_value, int | str):
        text: str = str(raw_value).strip()
        return None if text == "" else PaymentProviderReference(text)

    return None


def read_payment_status(raw_status: object) -> PaymentStatus:
    try:
        return PaymentStatus(str(raw_status).strip().lower())
    except ValueError as error:
        raise ValidationFailedError(
            "Payment notification has an unknown order status."
        ) from error


def read_money(raw_amount: object, raw_currency: object) -> Money | None:
    """Amount in minor units with its currency, when both are well-formed."""

    if isinstance(raw_amount, bool) or not isinstance(raw_currency, str):
        return None

    amount_text: str = (
        str(raw_amount).strip() if isinstance(raw_amount, int | str) else ""
    )
    if not amount_text.isdigit():
        return None

    try:
        return Money(
            amount_minor=MoneyAmountMinor(int(amount_text)),
            currency_code=CurrencyCode(raw_currency.strip().upper()),
        )
    except ValueError:
        return None


def read_failure_reason(raw_reason: object) -> PaymentFailureReason | None:
    if not isinstance(raw_reason, str) or raw_reason.strip() == "":
        return None

    return PaymentFailureReason(raw_reason.strip()[:MAX_FAILURE_REASON_LENGTH])
