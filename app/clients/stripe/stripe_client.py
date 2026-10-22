from collections.abc import Mapping
from typing import cast

import httpx

from app.clients.stripe.stripe_protocol import (
    FormValue,
    encode_form,
    parse_event,
    read_error,
    verify_signature,
)
from app.contracts.client_contract import ClientContract
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
)
from app.schemas.typings.platform.strings import PlatformSecret

DEFAULT_STRIPE_API_BASE_URL: str = "https://api.stripe.com"
# Every request and every webhook endpoint is pinned to this API version, so
# the shapes the adapter reads never change under it (docs/LAUNCH.md).
STRIPE_API_VERSION: str = "2024-06-20"
REQUEST_TIMEOUT_SECONDS: float = 15.0
CARD_ERROR_TYPE: str = "card_error"
PAYMENT_REQUIRED_STATUS: int = 402
NOT_FOUND_STATUS: int = 404


class StripeCardDeclinedError(ExternalServiceError):
    """Stripe refused to charge the card (HTTP 402, a card error)."""

    def __init__(self, decline_code: str) -> None:
        super().__init__(f"Stripe declined the card: {decline_code}.")
        self.decline_code: str = decline_code


class StripeNotFoundError(ExternalServiceError):
    """The object asked for does not exist (any more) at Stripe."""


class StripeClient(ClientContract):
    """
    Minimal client of the Stripe API (https://docs.stripe.com/api): Checkout
    in subscription mode, the billing portal, subscriptions, invoices,
    payment methods, and the verification of webhook signatures.

    Requests are form-encoded, authenticated with the secret key and pinned
    to STRIPE_API_VERSION; a POST that must not run twice carries an
    Idempotency-Key. Errors report Stripe's error type and code, never its
    message or the request.
    """

    def __init__(
        self,
        secret_key: PlatformSecret,
        webhook_secret: PlatformSecret | None,
        api_base_url: str = DEFAULT_STRIPE_API_BASE_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._webhook_secret: str | None = (
            None if webhook_secret is None else str(webhook_secret)
        )
        self._http_client: httpx.Client = httpx.Client(
            base_url=api_base_url.rstrip("/"),
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
            headers={
                "Authorization": f"Bearer {secret_key}",
                "Stripe-Version": STRIPE_API_VERSION,
            },
        )

    def create_checkout_session(
        self, parameters: Mapping[str, FormValue], idempotency_key: str
    ) -> dict[str, object]:
        return self._request(
            "POST", "/v1/checkout/sessions", parameters, idempotency_key
        )

    def create_billing_portal_session(
        self, parameters: Mapping[str, FormValue]
    ) -> dict[str, object]:
        return self._request("POST", "/v1/billing_portal/sessions", parameters)

    def cancel_subscription(self, subscription_id: str) -> None:
        """Cancel at once; one already gone counts as cancelled."""

        try:
            self._request("DELETE", f"/v1/subscriptions/{subscription_id}")
        except StripeNotFoundError:
            return

    def pay_invoice(self, invoice_id: str, idempotency_key: str) -> dict[str, object]:
        """
        Charge an open invoice again with its saved card.

        Raises:
            StripeCardDeclinedError: the card was declined.
        """

        return self._request(
            "POST", f"/v1/invoices/{invoice_id}/pay", {}, idempotency_key
        )

    def retrieve_subscription(self, subscription_id: str) -> dict[str, object]:
        """The subscription with its default payment method expanded."""

        return self._request(
            "GET",
            f"/v1/subscriptions/{subscription_id}",
            {"expand": ["default_payment_method"]},
        )

    def retrieve_payment_method(self, payment_method_id: str) -> dict[str, object]:
        return self._request("GET", f"/v1/payment_methods/{payment_method_id}")

    def verify_webhook(
        self, payload: str, signature_header: str | None, now_unix_seconds: int
    ) -> dict[str, object]:
        """
        The event of a webhook delivery whose signature is valid.

        Raises:
            AccessDeniedError: no signing secret, or a missing, wrong or
                stale signature.
            ValidationFailedError: the payload is not an event.
        """

        if self._webhook_secret is None or signature_header is None:
            raise AccessDeniedError("Payment notification cannot be verified.")

        verify_signature(
            payload, signature_header, self._webhook_secret, now_unix_seconds
        )
        return parse_event(payload)

    def _request(
        self,
        method: str,
        path: str,
        parameters: Mapping[str, FormValue] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        pairs: list[tuple[str, str]] = encode_form(parameters or {})
        headers: dict[str, str] = (
            {} if idempotency_key is None else {"Idempotency-Key": idempotency_key}
        )
        try:
            response: httpx.Response = self._http_client.request(
                method,
                path,
                params=tuple(pairs) if method == "GET" else None,
                data=None if method == "GET" else dict(pairs),
                headers=headers,
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Stripe request failed: {type(error).__name__}."
            ) from error

        return read_response(response)


def read_response(response: httpx.Response) -> dict[str, object]:
    try:
        body: object = response.json()
    except ValueError:
        body = None

    if response.status_code >= 400:
        error_type, code = read_error(body)
        if (
            response.status_code == PAYMENT_REQUIRED_STATUS
            or error_type == CARD_ERROR_TYPE
        ):
            raise StripeCardDeclinedError(code)

        if response.status_code == NOT_FOUND_STATUS:
            raise StripeNotFoundError(f"Stripe has no such object ({code}).")

        raise ExternalServiceError(
            f"Stripe returned HTTP {response.status_code} ({error_type}, {code})."
        )

    if not isinstance(body, dict):
        raise ExternalServiceError("Stripe returned an unreadable response.")

    return cast(dict[str, object], body)
