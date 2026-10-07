"""One Telegram Bot API call and how its refusals map to platform errors."""

import httpx

from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
    ValidationFailedError,
)
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_integer,
    read_object,
    read_text,
)
from app.utilities.channels.retry_after import read_retry_after_seconds

# Telegram answers 401 or 404 when the token is wrong or revoked (getMe while
# connecting; any later call means the bot stopped working). 403 is about
# one chat (the customer blocked the bot), not the bot.
REJECTED_TOKEN_ERROR_CODES: frozenset[int] = frozenset({401, 404})
# "Too Many Requests: retry after N" (`parameters.retry_after`).
RATE_LIMITED_ERROR_CODE: int = 429
CLIENT_ERROR_CODES: range = range(400, 500)


def call_bot_api(
    http_client: httpx.Client,
    bot_token: str,
    method_name: str,
    payload: JsonObject,
) -> object:
    """
    The method's `result`. The bot token is part of the request path, so
    it never appears in error messages and transport errors are not
    chained into them.
    """

    try:
        response: httpx.Response = http_client.post(
            f"/bot{bot_token}/{method_name}", json=payload
        )
    except httpx.HTTPError as error:
        # Chaining would carry the request URL, which contains the token.
        raise ExternalServiceError(
            f"Telegram {method_name} failed: {type(error).__name__}."
        ) from None

    body: JsonObject | None = parse_json_object(response.content)
    if body is None:
        raise ExternalServiceError(
            f"Telegram {method_name} returned HTTP {response.status_code} "
            "without a JSON body."
        )

    if body.get("ok") is True:
        return body.get("result")

    raise refusal_error(method_name, body, response)


def refusal_error(
    method_name: str, body: JsonObject, response: httpx.Response
) -> Exception:
    error_code: int = read_integer(body, "error_code") or response.status_code
    description: str = read_text(body, "description") or "unknown error"
    if method_name == "getMe" and error_code in REJECTED_TOKEN_ERROR_CODES:
        return ValidationFailedError(
            "Telegram rejected the bot token; copy it again from @BotFather."
        )

    if error_code == RATE_LIMITED_ERROR_CODE:
        parameters: JsonObject = read_object(body, "parameters") or {}
        return ProviderRateLimitedError(
            f"Telegram {method_name} is rate limited: {description}",
            retry_after_seconds=read_retry_after_seconds(
                read_integer(parameters, "retry_after"),
                response.headers.get("Retry-After"),
            ),
        )

    if error_code in REJECTED_TOKEN_ERROR_CODES:
        return ChannelCredentialRejectedError(
            f"Telegram {method_name} rejected the bot token ({error_code}: "
            f"{description})."
        )

    if CLIENT_ERROR_CODES.start <= error_code < CLIENT_ERROR_CODES.stop:
        # A refusal of this request (blocked bot, unknown chat, bad text):
        # sending it again cannot help.
        return ProviderRejectedMessageError(
            f"Telegram {method_name} refused the request ({error_code}): {description}"
        )

    return ExternalServiceError(
        f"Telegram {method_name} failed ({error_code}): {description}"
    )
