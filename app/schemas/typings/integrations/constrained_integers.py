"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ApiKeyCount(BaseConstrainedTypedInt):
    """How many API keys a business has (or may have)."""

    ge = 0
    le = 1000


class PublicApiRequestsPerMinute(BaseConstrainedTypedInt):
    """
    How many requests one API key may make in a minute
    (PUBLIC_API_REQUESTS_PER_MINUTE); more are refused with 429 and
    Retry-After.

    Example:
        limit = PublicApiRequestsPerMinute(120)
    """

    ge = 1
    le = 10_000


class WebhookAttemptCount(BaseConstrainedTypedInt):
    """How many times a delivery has been tried."""

    ge = 0
    le = 100


class WebhookEndpointCount(BaseConstrainedTypedInt):
    """How many webhook endpoints a business has (or may have)."""

    ge = 0
    le = 1000


class WebhookFailureCount(BaseConstrainedTypedInt):
    """
    How many delivery attempts to an endpoint failed in a row (a success
    starts it from zero again).
    """

    ge = 0
    le = 1_000_000


class WebhookFailuresBeforeDisable(BaseConstrainedTypedInt):
    """
    After how many failed attempts in a row an endpoint is switched off
    (WEBHOOK_DISABLE_AFTER_FAILURES); the owner switches it on again.

    Example:
        limit = WebhookFailuresBeforeDisable(15)
    """

    ge = 1
    le = 1000


# Keep abc order for all non example types, if possible.
