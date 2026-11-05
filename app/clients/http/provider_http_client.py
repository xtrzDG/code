"""
The one way the platform builds an HTTP client for a provider's API
(Stripe, Flitt, Meta, Telegram, Twilio, Google, Cal.com, ElevenLabs, S3,
Langfuse, Turnstile, web push), so every client has the same policy
(OWASP API10 Unsafe Consumption of APIs, ASVS V12.3.2, V15.3.2):

- TLS certificates are always verified (no `verify` argument exists);
- a timeout is required: connect within a few seconds, read within the
  client's budget (`provider_timeouts.py`);
- redirects are never followed: a provider answering 3xx is an error the
  client sees, not a hop to an address nobody vetted;
- the answer is read within a byte cap, counted after unpacking
  (`capped_response_stream.py`); a longer one fails like a broken
  connection (an `httpx.ReadError`), which every client already turns into
  its ExternalServiceError and its circuit breaker counts.

`tests/resilience/test_provider_http_clients.py` fails when code under
`app/` builds an `httpx.Client` any other way. Tenant-supplied addresses
never come here: they go through `SafeHttpFetcher` (SSRF guard).
"""

from collections.abc import Callable, Mapping

import httpx

from app.clients.http.capped_response_stream import cap_response

MEBIBYTE: int = 1024 * 1024
# JSON answers of provider APIs: the largest real one is far below this.
API_RESPONSE_MAX_BYTES: int = 8 * MEBIBYTE
# Customer files downloaded from a messenger (their own caps,
# MEDIA_MAX_*_BYTES of at most 25 MiB, are checked while reading).
MEDIA_RESPONSE_MAX_BYTES: int = 32 * MEBIBYTE
# Stored recordings and photos read back from object storage.
STORED_OBJECT_MAX_BYTES: int = 256 * MEBIBYTE
# A database backup streamed to disk for a restore drill.
BACKUP_OBJECT_MAX_BYTES: int = 64 * 1024 * MEBIBYTE
# Compressed answers are welcome, but only in codings unpacked under a cap.
ACCEPT_ENCODING: str = "gzip, deflate"

type ResponseHook = Callable[[httpx.Response], None]


def build_provider_http_client(
    *,
    timeout: httpx.Timeout | float,
    max_response_bytes: int,
    base_url: str = "",
    headers: Mapping[str, str] | None = None,
    auth: httpx.Auth | tuple[str, str] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """
    A client with the platform's policy. `transport` is for tests (an
    `httpx.MockTransport`); production uses httpx's own, which verifies
    certificates.
    """

    if max_response_bytes <= 0:
        raise ValueError("A provider client needs a positive response cap.")

    return httpx.Client(
        base_url=base_url,
        headers={"Accept-Encoding": ACCEPT_ENCODING, **(headers or {})},
        auth=auth,
        timeout=timeout,
        transport=transport,
        follow_redirects=False,
        verify=True,
        event_hooks={"response": [response_cap(max_response_bytes)]},
    )


def response_cap(max_bytes: int) -> ResponseHook:
    """The hook that caps every answer of one client."""

    def cap(response: httpx.Response) -> None:
        cap_response(response, max_bytes)

    return cap
