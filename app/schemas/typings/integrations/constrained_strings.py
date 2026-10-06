"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class ApiKeyName(BaseConstrainedTypedString):
    """
    The owner's name for an API key, shown in the key list: what it is for.

    Example:
        name = ApiKeyName("Zapier")
    """

    min_length = 1
    max_length = 60
    pattern = r"^\S(.*\S)?$"


class ApiKeyPrefix(BaseConstrainedTypedString):
    """
    The public start of an API key (`awk_` and eight characters), shown in
    the key list and the audit log so a key can be recognized; the rest of
    the key is never shown again after it was created.

    Example:
        prefix = ApiKeyPrefix("awk_abcd2345")
    """

    min_length = 12
    max_length = 12
    pattern = r"^awk_[a-z2-7]{8}$"


class ApiKeySecretHash(BaseConstrainedTypedString):
    """
    SHA-256 hex digest of a whole API key: what is stored and looked up
    (the key itself is not stored).

    Example:
        digest = ApiKeySecretHash("ab" * 32)
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}$"


class ApiKeyToken(BaseConstrainedTypedString):
    """
    A whole API key as a caller sends it (`Authorization: Bearer awk_…`):
    the prefix, an underscore and 40 random characters. It is shown once,
    when the key is created.

    Example:
        token = ApiKeyToken("awk_abcd2345_" + "A" * 40)
    """

    min_length = 53
    max_length = 53
    pattern = r"^awk_[a-z2-7]{8}_[A-Za-z0-9]{40}$"


class PublicTimestamp(BaseConstrainedTypedString):
    """
    A moment as the public API and webhooks write it: ISO 8601 with
    seconds and the offset (`Z` for UTC, the business's own offset for a
    booking's start and end).

    Example:
        moment = PublicTimestamp("2026-10-06T19:30:00+04:00")
    """

    min_length = 20
    max_length = 25
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$"


class WebhookEndpointLabel(BaseConstrainedTypedString):
    """
    The owner's note on a webhook endpoint (what receives it).

    Example:
        label = WebhookEndpointLabel("CRM: new bookings")
    """

    min_length = 1
    max_length = 80
    pattern = r"^\S(.*\S)?$"


class WebhookErrorText(BaseConstrainedTypedString):
    """
    Why the last attempt of a delivery failed, on one line, for the
    delivery log (no response body is kept).

    Example:
        error = WebhookErrorText("The address answered HTTP 500.")
    """

    min_length = 1
    max_length = 300


class WebhookSecretHint(BaseConstrainedTypedString):
    """
    The last four characters of a webhook's signing secret, shown so the
    owner can tell which secret a receiver holds.

    Example:
        hint = WebhookSecretHint("x9Qa")
    """

    min_length = 4
    max_length = 4
    pattern = r"^[A-Za-z0-9_-]{4}$"


class WebhookSignature(BaseConstrainedTypedString):
    """
    The `Workshop-Signature` header of a webhook request: the time it was
    signed (UNIX seconds) and the HMAC-SHA256 of `<time>.<body>` with the
    endpoint's secret, in hex (`t=1791234567,v1=…`).

    Example:
        signature = WebhookSignature("t=1791234567,v1=" + "ab" * 32)
    """

    min_length = 70
    max_length = 90
    pattern = r"^t=\d{1,12},v1=[0-9a-f]{64}$"


class WebhookSigningSecret(BaseConstrainedTypedString):
    """
    The secret a webhook receiver checks signatures with (`whsec_` and 43
    random URL-safe characters). Stored sealed; shown once, when the
    endpoint is created or its secret is replaced.

    Example:
        secret = WebhookSigningSecret("whsec_" + "A" * 43)
    """

    min_length = 49
    max_length = 49
    pattern = r"^whsec_[A-Za-z0-9_-]{43}$"


class WebhookTargetUrl(BaseConstrainedTypedString):
    """
    The https address events are sent to. It must be public: the address
    is checked when it is saved and the host again before every delivery
    (the SSRF guard).

    Example:
        url = WebhookTargetUrl("https://hooks.zapier.com/hooks/standard/1/abc/")
    """

    min_length = 12
    max_length = 2000
    pattern = r"^https://[^\s/?#@]+(/[^\s]*)?$"


# Keep abc order for all non example types, if possible.
