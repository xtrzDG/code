"""How the Meta Graph API's errors map to application errors."""

from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
    ValidationFailedError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.utilities.channels.json_values import (
    JsonObject,
    read_flag,
    read_integer,
    read_object,
    read_text,
)
from app.utilities.channels.retry_after import read_retry_after_seconds

# Graph error codes meaning the caller's token or object id is wrong:
# 100 invalid parameter / unknown object, 190 invalid token, 200 permission,
# 803 unknown alias.
INVALID_INPUT_ERROR_CODES: frozenset[int] = frozenset({100, 190, 200, 803})
# After connecting, these mean the page or system user token stopped working
# (expired, revoked, permissions removed): 401 / 403, Graph code 102
# (session) and 190 (invalid OAuth token).
REJECTED_CREDENTIAL_STATUS_CODES: frozenset[int] = frozenset({401, 403})
REJECTED_CREDENTIAL_ERROR_CODES: frozenset[int] = frozenset({102, 190})
# Graph error codes of a message template Meta refuses: 132000 wrong number
# of variables, 132001 no template of that name in that language, 132005
# translated text too long, 132007 policy, 132012 variable format, 132015
# paused, 132016 disabled.
WHATSAPP_TEMPLATE_ERROR_CODES: frozenset[int] = frozenset(
    {132000, 132001, 132005, 132007, 132012, 132015, 132016}
)
# Graph error codes asking to slow down: 4 app, 17 user, 32 page and 613
# call-rate limits, 80007 WhatsApp account rate limit, 130429 Cloud API
# throughput, 131048 spam rate limit, 131056 too many messages to one user.
RATE_LIMIT_ERROR_CODES: frozenset[int] = frozenset(
    {4, 17, 32, 613, 80007, 130429, 131048, 131056}
)
RATE_LIMITED_STATUS_CODE: int = 429
CLIENT_ERROR_STATUS_CODES: range = range(400, 500)


def build_graph_error(
    status_code: int,
    body: JsonObject,
    retry_after_header: str | None,
    is_lookup: bool,
) -> ApplicationError:
    """
    The error of a failed Graph call, most specific first: a lookup's wrong
    token or id (ValidationFailedError while connecting), a token that
    stopped working, a refused template, a request to slow down (429 or a
    throttling code, with Retry-After), another refusal of this request (a
    4xx Meta does not mark transient), else a temporary failure.
    """

    error: JsonObject = read_object(body, "error") or {}
    error_code: int | None = read_integer(error, "code")
    message: str = read_text(error, "message") or f"HTTP {status_code}"
    if is_lookup and error_code in INVALID_INPUT_ERROR_CODES:
        return ValidationFailedError(
            f"Meta did not accept the account or token: {message}"
        )

    described: str = f"{error_code or status_code}: {message}"
    if (
        status_code in REJECTED_CREDENTIAL_STATUS_CODES
        or error_code in REJECTED_CREDENTIAL_ERROR_CODES
    ):
        return ChannelCredentialRejectedError(
            f"Meta rejected the access token or its permissions ({described})"
        )

    if error_code in WHATSAPP_TEMPLATE_ERROR_CODES:
        return WhatsAppTemplateRejectedError(
            f"Meta refused the message template ({error_code}): {message}"
        )

    if status_code == RATE_LIMITED_STATUS_CODE or error_code in RATE_LIMIT_ERROR_CODES:
        return ProviderRateLimitedError(
            f"Meta asked to slow down ({described})",
            retry_after_seconds=read_retry_after_seconds(None, retry_after_header),
        )

    if status_code in CLIENT_ERROR_STATUS_CODES and not read_flag(
        error, "is_transient"
    ):
        return ProviderRejectedMessageError(f"Meta refused the request ({described})")

    return ExternalServiceError(f"Meta Graph API error {described}")
