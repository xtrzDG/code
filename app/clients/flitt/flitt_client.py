from collections.abc import Mapping

import httpx

from app.clients.flitt.flitt_protocol import (
    ENVELOPE_VERSION,
    RESPONSE_WRAPPER_KEY,
    build_envelope_signature,
    build_parameter_signature,
    decode_envelope_data,
    encode_envelope_data,
    is_envelope,
    is_signature_valid,
    parse_callback_parameters,
    require_mapping,
)
from app.contracts.client_contract import ClientContract
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

DEFAULT_FLITT_API_BASE_URL: str = "https://pay.flitt.com"
CHECKOUT_URL_PATH: str = "/api/checkout/url/"
SUBSCRIPTION_PATH: str = "/api/subscription/"
REQUEST_TIMEOUT_SECONDS: float = 15.0
SUCCESS_RESPONSE_STATUS: str = "success"
STOP_SUBSCRIPTION_ACTION: str = "stop"
MAX_REPORTED_ERROR_LENGTH: int = 200


class FlittClient(ClientContract):
    """
    Minimal client of the Flitt payment API (https://docs.flitt.com).

    Requests use protocol 2.0 (base64 JSON envelope signed with the payment
    key), which subscriptions with automatic charges require. Callbacks are
    accepted both as 2.0 envelopes and as flat signed parameters, in JSON or
    form encoding; every callback must carry this merchant id.
    """

    def __init__(
        self,
        merchant_id: PlatformIdentifier,
        secret_key: PlatformSecret,
        api_base_url: PublicBaseUrl | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._merchant_id: str = str(merchant_id).strip()
        self._secret_key: str = str(secret_key)
        base_url: str = (
            DEFAULT_FLITT_API_BASE_URL if api_base_url is None else str(api_base_url)
        )
        self._http_client: httpx.Client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def create_checkout_url(
        self,
        order_parameters: Mapping[str, object],
    ) -> dict[str, object]:
        """
        Create a hosted payment page; returns the response parameters with
        `checkout_url`. The merchant id is added here.

        Raises:
            ExternalServiceError: transport error, HTTP error, bad response
                signature, or a refusal by Flitt.
        """

        return self._post(CHECKOUT_URL_PATH, order_parameters)

    def stop_subscription(self, order_id: str) -> None:
        """Stop the automatic charges of a subscription order."""

        self._post(
            SUBSCRIPTION_PATH,
            {"order_id": order_id, "action": STOP_SUBSCRIPTION_ACTION},
        )

    def verify_callback(
        self,
        body: str,
        content_type: str | None,
    ) -> dict[str, object]:
        """
        Verified parameters of a server callback.

        Raises:
            ValidationFailedError: the body is malformed.
            AccessDeniedError: the signature or the merchant id is wrong.
        """

        parameters: dict[str, object] = parse_callback_parameters(body, content_type)
        if is_envelope(parameters):
            envelope_data: str = str(parameters["data"])
            if not is_signature_valid(
                build_envelope_signature(self._secret_key, envelope_data),
                parameters.get("signature"),
            ):
                raise AccessDeniedError("Payment notification signature is invalid.")

            parameters = decode_envelope_data(envelope_data)
        elif not is_signature_valid(
            build_parameter_signature(self._secret_key, parameters),
            parameters.get("signature"),
        ):
            raise AccessDeniedError("Payment notification signature is invalid.")

        if str(parameters.get("merchant_id", "")).strip() != self._merchant_id:
            raise AccessDeniedError(
                "Payment notification is for another merchant account."
            )

        return parameters

    def _post(
        self,
        path: str,
        order_parameters: Mapping[str, object],
    ) -> dict[str, object]:
        signed_parameters: dict[str, object] = {
            **order_parameters,
            "merchant_id": self._merchant_id_value(),
        }
        envelope_data: str = encode_envelope_data(signed_parameters)
        try:
            response: httpx.Response = self._http_client.post(
                path,
                json={
                    "request": {
                        "version": ENVELOPE_VERSION,
                        "data": envelope_data,
                        "signature": build_envelope_signature(
                            self._secret_key,
                            envelope_data,
                        ),
                    }
                },
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Flitt request failed: {type(error).__name__}."
            ) from error

        if response.status_code >= 400:
            raise ExternalServiceError(f"Flitt returned HTTP {response.status_code}.")

        return self._read_response(response)

    def _read_response(self, response: httpx.Response) -> dict[str, object]:
        try:
            body: dict[str, object] = require_mapping(response.json(), "Flitt response")
            result: dict[str, object] = require_mapping(
                body.get(RESPONSE_WRAPPER_KEY),
                "Flitt response",
            )
            if isinstance(result.get("data"), str):
                envelope_data: str = str(result["data"])
                signature: object = result.get("signature")
                if signature is not None and not is_signature_valid(
                    build_envelope_signature(self._secret_key, envelope_data),
                    signature,
                ):
                    raise ExternalServiceError("Flitt response signature is invalid.")

                result = {
                    **{key: value for key, value in result.items() if key != "data"},
                    **decode_envelope_data(envelope_data),
                }
        except (ValueError, ValidationFailedError) as error:
            raise ExternalServiceError(
                "Flitt returned an unreadable response."
            ) from error

        if result.get("response_status") != SUCCESS_RESPONSE_STATUS:
            raise ExternalServiceError(describe_flitt_error(result))

        return result

    def _merchant_id_value(self) -> int | str:
        return (
            int(self._merchant_id) if self._merchant_id.isdigit() else self._merchant_id
        )


def describe_flitt_error(result: Mapping[str, object]) -> str:
    """Flitt's error code, message and request id, without request data."""

    error_message: str = str(result.get("error_message", "unknown error"))
    error_code: object = result.get("error_code")
    request_id: object = result.get("request_id")
    details: list[str] = [error_message[:MAX_REPORTED_ERROR_LENGTH]]
    if error_code is not None:
        details.append(f"code {error_code}")

    if request_id is not None:
        details.append(f"request {request_id}")

    return "Flitt refused the request: " + ", ".join(details) + "."
